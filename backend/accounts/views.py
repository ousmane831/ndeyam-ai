import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import generics, mixins, serializers, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.permissions import IsPlatformAdmin
from governance.activity import log_activity

from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
    check_password_strength,
)
from .tokens import revoke_all_refresh_tokens

User = get_user_model()
logger = logging.getLogger(__name__)

DetailResponse = inline_serializer("DetailResponse", fields={"detail": serializers.CharField()})


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class AuthThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(AuthThrottleMixin, generics.GenericAPIView):
    """Inscription d'un éleveur avec création de son exploitation."""

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Créer un compte éleveur",
        responses={
            201: inline_serializer(
                "RegisterResponse",
                fields={
                    "user": UserSerializer(),
                    "access": serializers.CharField(),
                    "refresh": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        farm = user.farm_memberships.get().farm
        log_activity(request, "account.registered", user, actor=user, farm=farm)
        return Response(
            {"user": UserSerializer(user).data, **tokens_for(user)}, status=status.HTTP_201_CREATED
        )


class LoginView(AuthThrottleMixin, TokenObtainPairView):
    """Connexion par e-mail et mot de passe. Renvoie les jetons et le profil."""

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.get(pk=response.data["user"]["id"])
            log_activity(request, "auth.login", user, actor=user)
        return response


class RefreshView(TokenRefreshView):
    """Renouvelle le jeton d'accès. Le jeton de rafraîchissement est remplacé et l'ancien révoqué."""


class LogoutView(APIView):
    @extend_schema(summary="Se déconnecter", request=LogoutSerializer, responses={205: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token.get("user_id")) != str(request.user.pk):
                return Response({"detail": "Jeton invalide.", "code": "token_not_valid"}, status=400)
            token.blacklist()
        except TokenError:
            # Jeton déjà révoqué ou expiré : la session est de toute façon terminée.
            pass
        log_activity(request, "auth.logout", request.user)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """Profil de l'utilisateur connecté. Le rôle et l'e-mail ne sont pas modifiables ici."""

    http_method_names = ["get", "patch", "options"]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        return UserSerializer if self.request.method == "GET" else ProfileUpdateSerializer

    @extend_schema(request=ProfileUpdateSerializer, responses=UserSerializer)
    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_activity(
            request, "account.profile_updated", request.user, details={"fields": sorted(request.data.keys())}
        )
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    @extend_schema(
        summary="Changer son mot de passe", request=ChangePasswordSerializer, responses=DetailResponse
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password", "updated_at"])
        revoke_all_refresh_tokens(request.user)
        log_activity(request, "account.password_changed", request.user)
        return Response(
            {"detail": "Mot de passe modifié. Veuillez vous reconnecter sur vos autres appareils."}
        )


class PasswordResetRequestView(AuthThrottleMixin, APIView):
    """Envoie un lien de réinitialisation. La réponse est identique que le compte existe ou non."""

    permission_classes = [AllowAny]
    authentication_classes = []
    GENERIC_MESSAGE = (
        "Si un compte actif correspond à cette adresse, un e-mail de réinitialisation a été envoyé."
    )

    @extend_schema(
        summary="Demander la réinitialisation du mot de passe",
        request=PasswordResetRequestSerializer,
        responses=DetailResponse,
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL.rstrip('/')}/reinitialiser-mot-de-passe?uid={uid}&token={token}"
            send_mail(
                subject="NDEYAM AI — Réinitialisation de votre mot de passe",
                message=(
                    f"Bonjour {user.first_name or ''},\n\n"
                    "Une demande de réinitialisation du mot de passe de votre compte NDEYAM AI a été reçue.\n"
                    f"Pour choisir un nouveau mot de passe, ouvrez ce lien :\n\n{link}\n\n"
                    "Ce lien n'est utilisable qu'une seule fois. "
                    "Si vous n'êtes pas à l'origine de cette demande, "
                    "ignorez simplement ce message : votre mot de passe actuel reste inchangé.\n\n"
                    "L'équipe NDEYAM AI"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
            log_activity(request, "account.password_reset_requested", user, actor=user)
        return Response({"detail": self.GENERIC_MESSAGE})


class PasswordResetConfirmView(AuthThrottleMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    INVALID = "Ce lien de réinitialisation est invalide ou a expiré. Faites une nouvelle demande."

    @extend_schema(
        summary="Définir un nouveau mot de passe",
        request=PasswordResetConfirmSerializer,
        responses=DetailResponse,
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": self.INVALID, "code": "invalid_reset_link"}, status=400)
        try:
            check_password_strength(data["new_password"], user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.detail}) from exc
        user.set_password(data["new_password"])
        user.save(
            update_fields=["password", "updated_at"]
        )  # invalide aussi le lien (le jeton dépend du hash)
        revoke_all_refresh_tokens(user)
        log_activity(request, "account.password_reset_completed", user, actor=user)
        return Response({"detail": "Votre mot de passe a été réinitialisé. Vous pouvez vous connecter."})


class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Gestion des utilisateurs par les administrateurs. Pas de suppression : les comptes sont désactivés."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering_fields = ["email", "date_joined", "last_login", "role"]
    ordering = ["-date_joined"]
    http_method_names = ["get", "post", "patch", "options"]

    def get_queryset(self):
        return User.objects.annotate(
            farms_count=Count("farm_memberships", filter=Q(farm_memberships__is_active=True))
        )

    def perform_create(self, serializer):
        user = serializer.save()
        log_activity(self.request, "admin.user_created", user, details={"role": user.role})

    def perform_update(self, serializer):
        before = {"role": serializer.instance.role, "is_active": serializer.instance.is_active}
        user = serializer.save()
        if not user.is_active:
            revoke_all_refresh_tokens(user)
        log_activity(
            self.request,
            "admin.user_updated",
            user,
            details={"before": before, "after": {"role": user.role, "is_active": user.is_active}},
        )
