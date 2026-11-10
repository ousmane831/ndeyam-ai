"""
Catalogue anglais des messages du serveur (voir core/i18n_messages.py).

EXACT : {phrase française: traduction}. PATTERNS : [(expression régulière à groupes nommés, modèle anglais)].
Les modèles utilisent les noms de groupes entre accolades ; les accolades littérales s'écrivent {{ }}.
"""

EXACT = {
    # --- Erreurs génériques de l'API (core/exceptions.py, core/permissions.py, core/viewsets.py) ------------
    "Les données envoyées sont invalides.": "The data sent is invalid.",
    "Ressource introuvable.": "Resource not found.",
    "Une erreur interne est survenue.": "An internal error occurred.",
    "Suppression impossible : cet élément est encore utilisé.": "Cannot delete: this item is still in use.",
    "Cette action est réservée aux administrateurs de la plateforme.": (
        "This action is restricted to platform administrators."
    ),
    "Cette action est réservée aux experts et aux administrateurs.": (
        "This action is restricted to experts and administrators."
    ),
    "Cette action est réservée aux éleveurs et aux administrateurs.": (
        "This action is restricted to farmers and administrators."
    ),
    "Vous n'avez pas le droit de modifier les données de cette exploitation.": (
        "You are not allowed to modify this farm's data."
    ),
    "Vous ne pouvez pas ajouter de données dans cette exploitation.": "You cannot add data to this farm.",
    "Exploitation introuvable ou non modifiable avec votre compte.": (
        "Farm not found or not editable with your account."
    ),
    "Exploitation introuvable ou non modifiable.": "Farm not found or not editable.",
    "Exploitation introuvable ou non accessible.": "Farm not found or not accessible.",
    "Exploitation introuvable.": "Farm not found.",
    "Vous ne pouvez pas modifier les données de cette exploitation.": "You cannot modify this farm's data.",
    "Vous ne pouvez pas modifier cette exploitation.": "You cannot modify this farm.",
    "Doit appartenir à la même exploitation.": "Must belong to the same farm.",
    "Ce champ ne peut pas être modifié.": "This field cannot be changed.",
    # --- Contraintes de base de données (core/serializers.py, CHECK_MESSAGES) -------------------------------
    "L'année de la source n'est pas plausible.": "The source year is not plausible.",
    "Le poids initial doit être strictement positif.": "The initial weight must be strictly positive.",
    "Une teneur ne peut pas être négative.": "A content value cannot be negative.",
    "Le prix doit être strictement positif.": "The price must be strictly positive.",
    "La quantité disponible ne peut pas être négative.": "The available quantity cannot be negative.",
    "L'âge minimal doit être inférieur ou égal à l'âge maximal.": (
        "The minimum age must be less than or equal to the maximum age."
    ),
    "Le poids minimal doit être inférieur ou égal au poids maximal.": (
        "The minimum weight must be less than or equal to the maximum weight."
    ),
    "L'ingestion minimale doit être inférieure ou égale à la maximale.": (
        "The minimum intake must be less than or equal to the maximum intake."
    ),
    "Les âges, poids et quantités d'ingestion doivent être positifs.": (
        "Ages, weights and intake quantities must be positive."
    ),
    "Indiquez au moins une valeur (minimum, cible ou maximum).": (
        "Enter at least one value (minimum, target or maximum)."
    ),
    "Les valeurs d'un besoin ne peuvent pas être négatives.": "Requirement values cannot be negative.",
    "Le minimum doit être inférieur ou égal au maximum.": (
        "The minimum must be less than or equal to the maximum."
    ),
    "Le minimum doit être inférieur ou égal à la cible.": (
        "The minimum must be less than or equal to the target."
    ),
    "La cible doit être inférieure ou égale au maximum.": (
        "The target must be less than or equal to the maximum."
    ),
    "Choisissez un ingrédient ou une catégorie, pas les deux.": (
        "Choose an ingredient or a category, not both."
    ),
    "Indiquez au moins une borne (minimum ou maximum).": "Enter at least one bound (minimum or maximum).",
    "Les bornes doivent être comprises entre 0 et 100 % de la MS.": (
        "Bounds must be between 0 and 100 % of DM."
    ),
    "Le poids de l'animal doit être strictement positif.": "The animal's weight must be strictly positive.",
    "Une ration concerne un animal ou un lot, pas les deux.": (
        "A ration applies to an animal or a group, not both."
    ),
    "La date de fin doit être postérieure à la date de début.": "The end date must be after the start date.",
    "La quantité prévue doit être strictement positive.": "The planned quantity must be strictly positive.",
    "Une distribution concerne un animal ou un lot, pas les deux.": (
        "A feeding record applies to an animal or a group, not both."
    ),
    "Les quantités ne peuvent pas être négatives.": "Quantities cannot be negative.",
    "La quantité consommée ne peut pas dépasser la quantité distribuée.": (
        "The quantity consumed cannot exceed the quantity distributed."
    ),
    "La quantité refusée ne peut pas dépasser la quantité distribuée.": (
        "The quantity refused cannot exceed the quantity distributed."
    ),
    "Le poids doit être strictement positif.": "The weight must be strictly positive.",
    "Indiquez au moins une borne de GMD.": "Enter at least one ADG bound.",
    "Le GMD minimal doit être inférieur ou égal au GMD maximal.": (
        "The minimum ADG must be less than or equal to the maximum ADG."
    ),
    # --- Comptes (accounts) ---------------------------------------------------------------------------------
    "L'adresse e-mail est obligatoire.": "The email address is required.",
    "Un compte existe déjà avec cette adresse e-mail.": "An account already exists with this email address.",
    "Les deux mots de passe ne correspondent pas.": "The two passwords do not match.",
    "Adresse e-mail ou mot de passe incorrect, ou compte désactivé.": (
        "Incorrect email address or password, or account deactivated."
    ),
    "Le mot de passe actuel est incorrect.": "The current password is incorrect.",
    "Un mot de passe initial est obligatoire.": "An initial password is required.",
    "Vous ne pouvez pas désactiver votre propre compte.": "You cannot deactivate your own account.",
    "Vous ne pouvez pas retirer votre propre rôle d'administrateur.": (
        "You cannot remove your own administrator role."
    ),
    "Jeton invalide.": "Invalid token.",
    "Mot de passe modifié. Veuillez vous reconnecter sur vos autres appareils.": (
        "Password changed. Please sign in again on your other devices."
    ),
    "Si un compte actif correspond à cette adresse, un e-mail de réinitialisation a été envoyé.": (
        "If an active account matches this address, a reset email has been sent."
    ),
    "Ce lien de réinitialisation est invalide ou a expiré. Faites une nouvelle demande.": (
        "This reset link is invalid or has expired. Please make a new request."
    ),
    "Votre mot de passe a été réinitialisé. Vous pouvez vous connecter.": (
        "Your password has been reset. You can now sign in."
    ),
    # Rôles des comptes
    "Administrateur": "Administrator",
    "Éleveur": "Farmer",
    "Expert": "Expert",
    # --- Exploitations et membres (farms) -------------------------------------------------------------------
    "Indiquez le code pays à deux lettres (ex. SN).": "Enter the two-letter country code (e.g. SN).",
    "Le rôle de propriétaire ne peut pas être attribué ici.": "The owner role cannot be assigned here.",
    "L'adresse e-mail du membre est obligatoire.": "The member's email address is required.",
    "Aucun compte actif ne correspond à cette adresse. La personne doit d'abord s'inscrire.": (
        "No active account matches this address. The person must sign up first."
    ),
    "Cette personne est déjà membre de l'exploitation.": "This person is already a member of the farm.",
    "Le propriétaire de l'exploitation ne peut pas être modifié ici.": (
        "The farm owner cannot be changed here."
    ),
    "Le rôle est obligatoire.": "The role is required.",
    "Seul un compte de type Expert peut être invité comme expert.": (
        "Only an Expert account can be invited as an expert."
    ),
    "Un compte Expert ne peut être invité qu'en lecture seule (rôle Expert).": (
        "An Expert account can only be invited as read-only (Expert role)."
    ),
    "Seuls les éleveurs et les administrateurs peuvent créer une exploitation.": (
        "Only farmers and administrators can create a farm."
    ),
    "Seul le propriétaire de l'exploitation peut gérer ses membres.": (
        "Only the farm owner can manage its members."
    ),
    "Le propriétaire ne peut pas être retiré de son exploitation.": (
        "The owner cannot be removed from their farm."
    ),
    # Rôles dans une exploitation
    "Propriétaire": "Owner",
    "Gestionnaire": "Manager",
    "Expert invité (lecture seule)": "Invited expert (read-only)",
    # --- Animaux, lots, observations (animals) --------------------------------------------------------------
    "La race ne correspond pas à l'espèce choisie.": "The breed does not match the chosen species.",
    "La catégorie ne correspond pas à l'espèce choisie.": "The category does not match the chosen species.",
    "Le stade physiologique ne correspond pas à l'espèce choisie.": (
        "The physiological stage does not match the chosen species."
    ),
    "Le lot appartient à une autre exploitation.": "The group belongs to another farm.",
    "Le lot est réservé à une autre espèce.": "The group is reserved for another species.",
    "La date de naissance ne peut pas être dans le futur.": "The date of birth cannot be in the future.",
    "Cette espèce n'est pas encore prise en charge.": "This species is not supported yet.",
    "Un lot porte déjà ce nom dans cette exploitation.": (
        "A group with this name already exists on this farm."
    ),
    "Indiquez soit la date de naissance, soit l'âge estimé, pas les deux.": (
        "Enter either the date of birth or the estimated age, not both."
    ),
    "L'âge ne peut pas être négatif.": "The age cannot be negative.",
    "Ce numéro est déjà utilisé dans cette exploitation.": (
        "This ear tag number is already used on this farm."
    ),
    "La date ne peut pas être dans le futur.": "The date cannot be in the future.",
    "sexe : M ou F attendu.": "sexe: M or F expected.",
    "Enregistrement de l'animal": "Animal registered",
    "consommation non mesurée": "intake not measured",
    # Sexe, statut, type d'observation
    "Mâle": "Male",
    "Femelle": "Female",
    "Présent": "Present",
    "Vendu": "Sold",
    "Mort": "Dead",
    "Archivé": "Archived",
    "Générale": "General",
    "Alimentation": "Feeding",
    "Comportement": "Behaviour",
    "État de santé observé (non diagnostique)": "Observed health status (not a diagnosis)",
    "Reproduction": "Reproduction",
    # Libellés des parties variables (profil de lot, alertes)
    "espèce": "species",
    "race": "breed",
    "catégorie": "category",
    "stade": "stage",
    "stade physiologique": "physiological stage",
    "date de naissance ou âge estimé": "date of birth or estimated age",
    "aucun poids enregistré": "no weight recorded",
    # --- Pesées et croissance (growth) ----------------------------------------------------------------------
    "La date de pesée ne peut pas être dans le futur.": "The weighing date cannot be in the future.",
    "La pesée est antérieure à la date de naissance de l'animal.": (
        "The weighing is earlier than the animal's date of birth."
    ),
    "Le poids doit être supérieur à zéro.": "The weight must be greater than zero.",
    "Une pesée ne peut pas être déplacée vers un autre animal.": (
        "A weighing cannot be moved to another animal."
    ),
    "Cet animal n'est plus présent dans l'exploitation.": "This animal is no longer present on the farm.",
    "Une pesée existe déjà pour cet animal à cette date.": (
        "A weighing already exists for this animal on this date."
    ),
    "Ajoutez au moins une pesée.": "Add at least one weighing.",
    "500 pesées maximum par séance.": "500 weighings maximum per session.",
    "Un animal apparaît plusieurs fois dans la séance.": "An animal appears more than once in the session.",
    "Renseignez au moins une borne de GMD.": "Enter at least one ADG bound.",
    "La borne maximale doit être ≥ à la borne minimale.": "The maximum bound must be ≥ the minimum bound.",
    "Ne correspond pas à l'espèce de la plage.": "Does not match the range's species.",
    "Vous ne pouvez pas enregistrer de pesée dans cette exploitation.": (
        "You cannot record weighings on this farm."
    ),
    "Aucune pesée n'a été enregistrée : corrigez les lignes en erreur.": (
        "No weighing was recorded: correct the rows with errors."
    ),
    "Les deux mesures doivent être séparées d'au moins un jour.": (
        "The two measurements must be at least one day apart."
    ),
    "Au moins deux pesées à des dates différentes sont nécessaires pour calculer un GMD.": (
        "At least two weighings on different dates are needed to calculate an ADG."
    ),
    "GMD = (poids final − poids initial) / nombre de jours écoulés": (
        "ADG = (final weight − initial weight) / number of days elapsed"
    ),
    "Comparaison à une plage de suivi validée. Il ne s'agit pas d'un diagnostic vétérinaire.": (
        "Comparison with a validated monitoring range. This is not a veterinary diagnosis."
    ),
    "Aucune plage de suivi validée ne s'applique à cet animal : aucune comparaison n'est effectuée.": (
        "No validated monitoring range applies to this animal: no comparison is made."
    ),
    "La moyenne ne porte que sur les animaux ayant au moins deux mesures à dates différentes.": (
        "The average only covers animals with at least two measurements on different dates."
    ),
    (
        "Aucun modèle de prédiction n'est disponible : il sera développé lorsque suffisamment de données "
        "réelles et représentatives auront été collectées."
    ): (
        "No prediction model is available: one will be developed once enough real, "
        "representative data has been collected."
    ),
    # Méthodes de pesée
    "Balance / bascule": "Scale / weighbridge",
    "Ruban barymétrique": "Weight tape",
    "Estimation visuelle": "Visual estimate",
    # --- Rations et alimentation (feeding) ------------------------------------------------------------------
    "Cette formule a été rejetée par un expert : elle ne peut pas devenir une ration.": (
        "This formula was rejected by an expert: it cannot become a ration."
    ),
    (
        "Seule une formule validée par un expert peut devenir une ration. "
        "Demandez d'abord la vérification de cette estimation."
    ): (
        "Only a formula validated by an expert can become a ration. First request an expert review of this "
        "estimate."
    ),
    "Associez soit un animal, soit un lot (l'un des deux, pas les deux).": (
        "Link either an animal or a group (one of them, not both)."
    ),
    "La date de fin doit suivre la date de début.": "The end date must come after the start date.",
    "La quantité doit être positive.": "The quantity must be positive.",
    "L'animal ou le lot doit être celui de la ration.": "The animal or group must be the ration's.",
    "Ne peut pas dépasser la quantité distribuée.": "Cannot exceed the quantity distributed.",
    "La quantité ne peut pas être négative.": "The quantity cannot be negative.",
    "Indiquez le nombre d'animaux nourris dans le lot.": "Enter the number of animals fed in the group.",
    (
        "La consommation totale ne couvre que les distributions où elle a été mesurée ; "
        "le coût ne couvre que les distributions dont la formule a un coût connu."
    ): (
        "Total intake only covers feedings where it was measured; "
        "the cost only covers feedings whose formula has a known cost."
    ),
    # Statut d'une ration
    "En cours": "Ongoing",
    "Terminée": "Ended",
    # --- Formules : saisie, revue, comparaison (formulations) -----------------------------------------------
    "Doit appartenir à la même exploitation que la formule.": "Must belong to the same farm as the formula.",
    "Ajoutez au moins un ingrédient avec sa quantité.": "Add at least one ingredient with its quantity.",
    "Chaque ingrédient ne doit apparaître qu'une fois.": "Each ingredient must appear only once.",
    "Seules les formules manuelles sont modifiables ainsi.": "Only manual formulas can be edited this way.",
    "L'animal ou le lot doit appartenir à l'exploitation choisie.": (
        "The animal or group must belong to the chosen farm."
    ),
    "Indiquez l'espèce ou choisissez un animal ou un lot.": (
        "Enter the species or choose an animal or a group."
    ),
    "La référence concerne une autre espèce.": "The reference applies to another species.",
    "Une exploitation DEMO n'utilise que des références DEMO.": "A DEMO farm only uses DEMO references.",
    (
        "Cette référence n'est pas utilisable : seules les références validées (non DEMO) "
        "le sont pour une exploitation réelle."
    ): "This reference cannot be used: only validated (non-DEMO) references can be used for a real farm.",
    "Proposez au moins un ingrédient.": "Offer at least one ingredient.",
    "Un ingrédient appartient à une autre exploitation.": "An ingredient belongs to another farm.",
    "Pour tenir compte des quantités disponibles, indiquez le nombre d'animaux et la durée (jours).": (
        "To take available quantities into account, enter the number of animals and the duration (days)."
    ),
    "Seul un expert invité sur l'exploitation ou un administrateur peut se prononcer.": (
        "Only an expert invited to the farm or an administrator can decide."
    ),
    "Un commentaire est obligatoire.": "A comment is required.",
    "Une formule DEMO ne peut pas être validée.": "A DEMO formula cannot be validated.",
    "La formule ne contient aucun ingrédient.": "The formula contains no ingredients.",
    "Indiquez entre 2 et 5 formules à comparer.": "Choose between 2 and 5 formulas to compare.",
    "Formule introuvable.": "Formula not found.",
    (
        "Comparaison d'estimations : seules les formules au statut « Validée » ont été vérifiées par un "
        "expert."
    ): (
        "Comparison of estimates: only formulas with the “Validated” status have been reviewed by an expert."
    ),
    (
        "Apports estimés à partir des seules compositions validées. Il ne s'agit pas d'une recommandation "
        "nutritionnelle validée."
    ): (
        "Supplies estimated from validated compositions only. This is not a validated nutritional "
        "recommendation."
    ),
    # Modes et statuts des formules
    "Économique (coût minimal)": "Economic (least cost)",
    "Équilibré (objectifs nutritionnels)": "Balanced (nutritional targets)",
    "Économique": "Economic",
    "Équilibré": "Balanced",
    "Saisie manuelle": "Manual entry",
    "Calcul refusé (données insuffisantes)": "Calculation refused (insufficient data)",
    "Aucune solution (contraintes incompatibles)": "No solution (incompatible constraints)",
    "Estimation mathématique": "Mathematical estimate",
    "En attente de vérification": "Awaiting expert review",
    "Validée par un expert": "Validated by an expert",
    "Rejetée par un expert": "Rejected by an expert",
    # --- Moteur de formulation (formulations/engine, engine_service) ----------------------------------------
    "Aucun besoin nutritionnel validé n'est disponible pour ce profil d'animal.": (
        "No validated nutritional requirement is available for this animal profile."
    ),
    (
        "L'ingestion de matière sèche (kg MS/jour) n'est pas renseignée dans la référence nutritionnelle : "
        "impossible de dimensionner la ration."
    ): "Dry matter intake (kg DM/day) is not given in the nutritional reference: the ration cannot be sized.",
    "Aucun ingrédient n'a été proposé.": "No ingredient was offered.",
    "teneur en matière sèche inconnue": "dry matter content unknown",
    "prix inconnu (indispensable en mode économique)": "price unknown (required in economic mode)",
    "quantité disponible nulle": "no quantity available",
    "donnée DEMO interdite dans une exploitation réelle": "DEMO data is not allowed on a real farm",
    "seules des données DEMO sont utilisées dans une exploitation DEMO": (
        "only DEMO data is used on a DEMO farm"
    ),
    "Aucun ingrédient proposé ne dispose de toutes les données validées nécessaires.": (
        "None of the offered ingredients has all the required validated data."
    ),
    "Certains prix sont inconnus : le coût n'est pas pris en compte ni calculé.": (
        "Some prices are unknown: cost is neither taken into account nor calculated."
    ),
    (
        "Aucune cible n'est définie dans la référence : le mode équilibré se limite au respect des "
        "contraintes "
        "(avec le coût comme critère s'il est connu)."
    ): (
        "No target is defined in the reference: balanced mode is limited to meeting the constraints "
        "(with cost as a criterion if known)."
    ),
    (
        "Aucune ration ne permet de respecter simultanément toutes les contraintes avec les ingrédients "
        "proposés. "
        "Ajoutez des ingrédients, vérifiez les disponibilités ou faites revoir les contraintes par un expert."
    ): (
        "No ration can meet all the constraints at once with the offered ingredients. "
        "Add ingredients, check availabilities or have the constraints reviewed by an expert."
    ),
    "Le recalcul indépendant révèle une contrainte non respectée : la ration n'est pas conforme.": (
        "The independent recalculation shows an unmet constraint: the ration does not comply."
    ),
    (
        "Estimation mathématique calculée à partir des seules données validées. "
        "Elle ne constitue pas une recommandation nutritionnelle validée tant qu'un expert ne l'a pas "
        "vérifiée."
    ): (
        "Mathematical estimate calculated from validated data only. "
        "It is not a validated nutritional recommendation until an expert has reviewed it."
    ),
    (
        "Aucune référence nutritionnelle validée ne correspond à ce profil d'animal "
        "(espèce, catégorie, stade, objectif, poids, âge). "
        "Un expert doit d'abord saisir et valider une référence sourcée."
    ): (
        "No validated nutritional reference matches this animal profile "
        "(species, category, stage, objective, weight, age). "
        "An expert must first enter and validate a sourced reference."
    ),
    "Aucune référence DEMO ne correspond à ce profil.": "No DEMO reference matches this profile.",
    "Calcul de DÉMONSTRATION réalisé avec des données fictives : ne pas utiliser pour nourrir des animaux.": (
        "DEMONSTRATION calculation made with fictitious data: do not use it to feed animals."
    ),
    "Source non renseignée (DEMO)": "Source not given (DEMO)",
    "non lancé": "not run",
    "Ingestion de matière sèche": "Dry matter intake",
    "apport journalier": "daily supply",
    "teneur": "content",
    # Unités
    "kg MS/jour": "kg DM/day",
    "kg brut/jour": "kg as fed/day",
    "fraction de la MS": "fraction of DM",
    "% MS": "% DM",
    "kg MS": "kg DM",
    "kg brut": "kg as fed",
    # --- Nutrition : ingrédients, compositions, prix, références, contraintes -------------------------------
    "La teneur en matière sèche doit être comprise entre 0 et 1000 g/kg brut.": (
        "The dry matter content must be between 0 and 1000 g/kg as fed."
    ),
    "Cet ingrédient privé appartient à une autre exploitation.": (
        "This private ingredient belongs to another farm."
    ),
    "La référence ne contient aucun besoin nutritionnel.": (
        "The reference contains no nutritional requirement."
    ),
    "Ne correspond pas à l'espèce de la référence.": "Does not match the reference's species.",
    "L'ingestion de matière sèche se renseigne dans les bornes d'ingestion de la référence.": (
        "Dry matter intake is entered in the reference's intake bounds."
    ),
    "Un ingrédient ne peut pas changer de catalogue.": "An ingredient cannot change catalogue.",
    "Un ingrédient porte déjà ce nom dans ce catalogue.": (
        "An ingredient with this name already exists in this catalogue."
    ),
    "Ce champ ne peut pas être modifié ; créez une nouvelle valeur.": (
        "This field cannot be changed; create a new value."
    ),
    "Une valeur existe déjà pour ce nutriment avec cette source : modifiez-la plutôt.": (
        "A value already exists for this nutrient with this source: edit it instead."
    ),
    "La composition d'un ingrédient DEMO doit être marquée DEMO.": (
        "The composition of a DEMO ingredient must be marked DEMO."
    ),
    "Code devise ISO à 3 lettres attendu (ex. XOF).": "3-letter ISO currency code expected (e.g. XOF).",
    "Le prix doit être supérieur à zéro.": "The price must be greater than zero.",
    "Renseignez au moins une valeur (minimum, cible ou maximum).": (
        "Enter at least one value (minimum, target or maximum)."
    ),
    "Les valeurs ne peuvent pas être négatives.": "Values cannot be negative.",
    "Le maximum doit être supérieur ou égal au minimum.": (
        "The maximum must be greater than or equal to the minimum."
    ),
    "La cible doit être comprise entre le minimum et le maximum.": (
        "The target must be between the minimum and the maximum."
    ),
    "Ce besoin est déjà défini pour cette référence.": (
        "This requirement is already defined for this reference."
    ),
    "Impossible de changer de système : des besoins y sont déjà exprimés.": (
        "Cannot change system: requirements are already expressed in it."
    ),
    "Choisissez soit un ingrédient, soit une catégorie d'ingrédients.": (
        "Choose either an ingredient or an ingredient category."
    ),
    "Les contraintes portent sur le catalogue commun uniquement.": (
        "Constraints apply to the shared catalogue only."
    ),
    "Renseignez au moins une borne.": "Enter at least one bound.",
    "Les bornes sont des pourcentages entre 0 et 100.": "Bounds are percentages between 0 and 100.",
    "Le maximum doit être ≥ au minimum.": "The maximum must be ≥ the minimum.",
    "Teneur en matière sèche inconnue : conversion impossible.": (
        "Dry matter content unknown: conversion impossible."
    ),
    "Vous ne pouvez pas modifier cet ingrédient.": "You cannot modify this ingredient.",
    "Le catalogue commun est géré par les experts. Choisissez votre exploitation pour un ingrédient privé.": (
        "The shared catalogue is managed by experts. Choose your farm for a private ingredient."
    ),
    "Vous ne pouvez pas modifier la composition de cet ingrédient.": (
        "You cannot modify this ingredient's composition."
    ),
    "Ingrédient introuvable.": "Ingredient not found.",
    "L'import des compositions est réservé aux experts et administrateurs.": (
        "Importing compositions is restricted to experts and administrators."
    ),
    "Besoins modifiés après validation.": "Requirements changed after validation.",
    "Un besoin ne peut pas être déplacé vers une autre référence.": (
        "A requirement cannot be moved to another reference."
    ),
    "âge": "age",
    "poids": "weight",
    "ingestion": "intake",
    # Catégories de nutriments, bases d'expression
    "Matière sèche": "Dry matter",
    "Énergie": "Energy",
    "Protéines / azote": "Protein / nitrogen",
    "Fibres": "Fibre",
    "Matières grasses": "Fat",
    "Minéraux": "Minerals",
    "par kg de matière sèche": "per kg of dry matter",
    "par kg de produit brut": "per kg as fed",
    "Quantité par animal et par jour": "Quantity per animal per day",
    "Teneur de la ration (par kg de MS)": "Ration content (per kg of DM)",
    # --- Imports CSV (core/csv_io.py, animals/imports.py, nutrition/imports.py) -----------------------------
    "Aucun fichier reçu (champ « file »).": "No file received (“file” field).",
    "Fichier trop volumineux (5 Mo maximum).": "File too large (5 MB maximum).",
    "Le fichier est vide.": "The file is empty.",
    "ingredient : nom manquant.": "ingredient: name missing.",
    "valeur : une teneur ne peut pas être négative.": "valeur: a content value cannot be negative.",
    "valeur : la matière sèche doit être comprise entre 0 et 1000 g/kg brut.": (
        "valeur: dry matter must be between 0 and 1000 g/kg as fed."
    ),
    "categorie : code obligatoire et valide pour un nouvel ingrédient.": (
        "categorie: a valid code is required for a new ingredient."
    ),
    "ingredient : statut DEMO différent de celui de l'import ; mélange interdit.": (
        "ingredient: DEMO status differs from the import's; mixing is not allowed."
    ),
    "date_reference : format attendu AAAA-MM-JJ.": "date_reference: expected format YYYY-MM-DD.",
    "valeur déjà VALIDÉE pour cette source : modification à faire manuellement par un expert.": (
        "value already VALIDATED for this source: an expert must change it manually."
    ),
    "Une source DEMO ne peut alimenter que des données DEMO.": "A DEMO source can only feed DEMO data.",
    # Statuts d'import
    "En attente": "Pending",
    "Terminé": "Completed",
    "Terminé avec erreurs": "Completed with errors",
    "Échec": "Failed",
    # --- Gouvernance des données (validation, sources, journal d'activité) ----------------------------------
    "Seuls les experts et les administrateurs peuvent modifier les données de référence.": (
        "Only experts and administrators can modify reference data."
    ),
    "Une donnée DEMO ne peut pas être validée.": "DEMO data cannot be validated.",
    "Une source documentaire doit être associée avant validation.": (
        "A source document must be linked before validation."
    ),
    "La source associée est une source DEMO : elle ne peut pas justifier une validation.": (
        "The linked source is a DEMO source: it cannot justify a validation."
    ),
    "Action de validation inconnue.": "Unknown validation action.",
    "Seuls les experts et les administrateurs peuvent effectuer cette action.": (
        "Only experts and administrators can perform this action."
    ),
    "Un commentaire est obligatoire pour rejeter une donnée.": "A comment is required to reject data.",
    "Donnée modifiée après validation.": "Data changed after validation.",
    # Statuts de validation et décisions
    "Brouillon": "Draft",
    "En attente de validation": "Awaiting validation",
    "Validé": "Validated",
    "Rejeté": "Rejected",
    "Soumis à validation": "Submitted for validation",
    "Remis en brouillon": "Returned to draft",
    # Types de sources
    "Table de composition / référentiel": "Composition table / reference framework",
    "Ouvrage": "Book",
    "Article scientifique": "Scientific article",
    "Rapport technique": "Technical report",
    "Analyse de laboratoire": "Laboratory analysis",
    "Enquête / mesure de terrain": "Field survey / measurement",
    "Avis d'expert documenté": "Documented expert opinion",
    "Site web / base en ligne": "Website / online database",
    "Autre": "Other",
    # Journal d'activité : objets et actions
    "création": "created",
    "modification": "updated",
    "suppression": "deleted",
    "Lot": "Group",
    "Animal": "Animal",
    "Ration": "Ration",
    "Distribution": "Feeding",
    "Formule": "Formula",
    "Pesée": "Weighing",
    "Prix": "Price",
    "Ingrédient": "Ingredient",
    "Composition": "Composition",
    "Référence nutritionnelle": "Nutritional reference",
    "Source documentaire": "Source document",
    "Document technique": "Technical document",
    "Connexion": "Sign-in",
    "Déconnexion": "Sign-out",
    "Création du compte": "Account created",
    "Profil modifié": "Profile updated",
    "Mot de passe modifié": "Password changed",
    "Réinitialisation du mot de passe demandée": "Password reset requested",
    "Mot de passe réinitialisé": "Password reset",
    "Compte créé par un administrateur": "Account created by an administrator",
    "Compte modifié par un administrateur": "Account updated by an administrator",
    "Création d'une exploitation": "Farm created",
    "Modification de l'exploitation": "Farm updated",
    "Ajout d'un membre": "Member added",
    "Modification d'un membre": "Member updated",
    "Retrait d'un membre": "Member removed",
    "Sortie d'un animal": "Animal removed from herd",
    "Retour d'un animal": "Animal returned to herd",
    "Observation ajoutée": "Observation added",
    "Séance de pesée": "Weighing session",
    "Formule calculée": "Formula calculated",
    "Formule soumise à un expert": "Formula submitted to an expert",
    "Formule validée par un expert": "Formula validated by an expert",
    "Formule rejetée par un expert": "Formula rejected by an expert",
    "Ration terminée": "Ration ended",
    "Alerte prise en compte": "Alert acknowledged",
    "Alerte résolue": "Alert resolved",
    "Alerte ignorée": "Alert dismissed",
    "Règle d'alerte créée": "Alert rule created",
    "Règle d'alerte modifiée": "Alert rule updated",
    "Donnée soumise à validation": "Data submitted for validation",
    "Donnée validée": "Data validated",
    "Donnée rejetée": "Data rejected",
    "Donnée remise en brouillon": "Data returned to draft",
    "Donnée remise en brouillon après modification": "Data returned to draft after changes",
    "Import d'animaux": "Animal import",
    "Import de compositions": "Composition import",
    "Document importé": "Document imported",
    "Document réindexé": "Document re-indexed",
    "Question à l'assistant": "Question to the assistant",
    "Erreur de l'assistant": "Assistant error",
    # --- Alertes et rappels (alerts) ------------------------------------------------------------------------
    "Rappel de pesée": "Weighing reminder",
    "Rappel de suivi": "Follow-up reminder",
    "Rappel de suivi alimentaire": "Feeding follow-up reminder",
    "Information manquante": "Missing information",
    "Informations manquantes": "Missing information",
    "Donnée de référence à valider": "Reference data to validate",
    "Données de référence à valider": "Reference data to validate",
    "Formulation à vérifier": "Formulation to review",
    "Croissance hors plage de suivi": "Growth outside monitoring range",
    "Information": "Information",
    "Attention": "Warning",
    "Important": "Important",
    "Ouverte": "Open",
    "Prise en compte": "Acknowledged",
    "Résolue": "Resolved",
    "Ignorée": "Dismissed",
    "Animal non pesé depuis l'intervalle de suivi choisi par l'exploitation.": (
        "Animal not weighed within the monitoring interval chosen by the farm."
    ),
    "Intervalle entre deux pesées (jours)": "Interval between two weighings (days)",
    "Ration en cours sans distribution enregistrée depuis le délai choisi.": (
        "Ongoing ration with no feeding recorded within the chosen delay."
    ),
    "Délai sans enregistrement (jours)": "Delay without records (days)",
    "Informations d'un animal nécessaires au suivi et à la formulation.": (
        "Animal information needed for monitoring and formulation."
    ),
    "Dernier GMD mesuré en dehors d'une plage de suivi validée par un expert.": (
        "Latest measured ADG outside a monitoring range validated by an expert."
    ),
    "Formule en attente de vérification par un expert.": "Formula awaiting expert review.",
    "Données de référence soumises, en attente de validation (experts, administrateurs).": (
        "Reference data submitted, awaiting validation (experts, administrators)."
    ),
    "Réglages de suivi propres à l'exploitation, pas des recommandations zootechniques.": (
        "Monitoring settings specific to the farm, not zootechnical recommendations."
    ),
    (
        "Cette formule a été soumise à un expert. Elle ne doit pas être considérée comme validée "
        "tant que l'expert ne s'est pas prononcé."
    ): (
        "This formula has been submitted to an expert. It must not be considered validated until the "
        "expert has decided."
    ),
    "aucune distribution enregistrée": "no feeding recorded",
    "automatique : condition plus remplie": "automatic: condition no longer met",
    "Cette règle concerne uniquement les experts (plateforme).": (
        "This rule only concerns experts (platform)."
    ),
    "Une règle de ce type existe déjà pour ce périmètre.": (
        "A rule of this type already exists for this scope."
    ),
    "Vous ne pouvez pas modifier cette alerte (accès en lecture seule).": (
        "You cannot modify this alert (read-only access)."
    ),
    "Les règles par défaut de la plateforme sont gérées par les administrateurs.": (
        "The platform's default rules are managed by administrators."
    ),
    "Vous ne pouvez pas modifier les réglages de cette exploitation.": (
        "You cannot modify this farm's settings."
    ),
    # --- Tableau de bord (core/dashboard.py) ----------------------------------------------------------------
    "Non renseignée": "Not specified",
    (
        "Moyenne des pesées de chaque mois, tous animaux confondus : les animaux pesés changent d'un mois à "
        "l'autre, ce n'est pas la courbe d'un animal."
    ): (
        "Monthly average of all weighings, all animals combined: the animals weighed change from one month "
        "to the next, so this is not one animal's curve."
    ),
    # --- Base documentaire (knowledge_base) -----------------------------------------------------------------
    "Fichier trop volumineux (20 Mo maximum).": "File too large (20 MB maximum).",
    "Seuls les fichiers PDF sont acceptés.": "Only PDF files are accepted.",
    "Le PDF est protégé par un mot de passe.": "The PDF is password-protected.",
    "Fichier PDF illisible ou endommagé.": "Unreadable or damaged PDF file.",
    (
        "Aucun texte n'a pu être extrait : le document est probablement scanné (image). "
        "La reconnaissance de caractères (OCR) n'est pas prise en charge dans cette version."
    ): (
        "No text could be extracted: the document is probably scanned (image). "
        "Optical character recognition (OCR) is not supported in this version."
    ),
    "Le document doit être indexé avec succès avant d'être validé.": (
        "The document must be indexed successfully before it is validated."
    ),
    "Aucun fournisseur d'embeddings configuré : le document est indexé en plein texte uniquement.": (
        "No embedding provider configured: the document is indexed for full-text search only."
    ),
    "Aucun fournisseur d'embeddings configuré : recherche plein texte uniquement.": (
        "No embedding provider configured: full-text search only."
    ),
    "Le fournisseur n'a pas renvoyé un vecteur par passage.": (
        "The provider did not return one vector per passage."
    ),
    "EMBEDDING_MODEL et EMBEDDING_BASE_URL doivent être renseignés.": (
        "EMBEDDING_MODEL and EMBEDDING_BASE_URL must be set."
    ),
    "EMBEDDING_API_KEY doit être renseignée pour ce fournisseur.": (
        "EMBEDDING_API_KEY must be set for this provider."
    ),
    "Dimensions d'embedding incompatibles : réindexez les documents avec le modèle actuel.": (
        "Incompatible embedding dimensions: re-index the documents with the current model."
    ),
    (
        "Le stockage pgvector n'est pas encore activé dans cette version : utilisez "
        "VECTOR_STORE_BACKEND=numpy."
    ): ("pgvector storage is not enabled yet in this version: use VECTOR_STORE_BACKEND=numpy."),
    "Le chevauchement doit être inférieur à la taille des passages.": (
        "The overlap must be smaller than the passage size."
    ),
    "Saisissez une question ou des mots-clés.": "Enter a question or keywords.",
    "Aucun passage vectorisé avec le modèle actuel : recherche plein texte.": (
        "No passage embedded with the current model: full-text search."
    ),
    "Aucun passage ne correspond dans les documents disponibles.": (
        "No passage matches in the available documents."
    ),
    "Une source DEMO ne peut accompagner qu'un document DEMO.": (
        "A DEMO source can only accompany a DEMO document."
    ),
    "La base documentaire est gérée par les experts et les administrateurs.": (
        "The document library is managed by experts and administrators."
    ),
    "Recherche sémantique disponible (repli sur le plein texte si nécessaire).": (
        "Semantic search available (falls back to full text if needed)."
    ),
    # Statuts de traitement des documents
    "Importé": "Uploaded",
    "En cours de traitement": "Processing",
    "Indexé": "Indexed",
    "Échec du traitement": "Processing failed",
    # --- Assistant IA (messages destinés à l'utilisateur, pas au modèle) ------------------------------------
    "L'assistant a dépassé le nombre d'étapes autorisé pour cette question.": (
        "The assistant exceeded the number of steps allowed for this question."
    ),
    "Clé API du fournisseur refusée : vérifiez LLM_API_KEY.": "Provider API key rejected: check LLM_API_KEY.",
    "Le fournisseur d'IA est momentanément saturé. Réessayez dans un instant.": (
        "The AI provider is temporarily overloaded. Try again in a moment."
    ),
    "Le fournisseur d'IA est injoignable (réseau ou délai dépassé).": (
        "The AI provider cannot be reached (network or timeout)."
    ),
    "Le modèle a refusé de répondre à cette demande.": "The model declined to answer this request.",
    "L'assistant IA n'est pas configuré (LLM_PROVIDER=none).": (
        "The AI assistant is not configured (LLM_PROVIDER=none)."
    ),
    "LLM_API_KEY doit être renseignée pour ce fournisseur.": "LLM_API_KEY must be set for this provider.",
    "LLM_BASE_URL doit être renseignée pour ce fournisseur.": "LLM_BASE_URL must be set for this provider.",
    "LLM_MODEL doit être renseigné pour ce fournisseur.": "LLM_MODEL must be set for this provider.",
    (
        "L'assistant IA n'est pas configuré sur cette installation. Les autres modules (animaux, pesées, "
        "formulation, rations, base documentaire) restent entièrement utilisables."
    ): (
        "The AI assistant is not configured on this installation. The other modules (animals, weighings, "
        "formulation, rations, document library) remain fully usable."
    ),
    "Assistant disponible.": "Assistant available.",
    "Je n'ai pas pu formuler de réponse. Reformulez votre question.": (
        "I could not formulate an answer. Please rephrase your question."
    ),
    "Rédaction et explications générées par le modèle de langage": (
        "Wording and explanations generated by the language model"
    ),
    "Exploitations": "Farms",
    "Animaux enregistrés": "Registered animals",
    "Lots": "Groups",
    "Historique alimentaire": "Feeding history",
    "Formules enregistrées": "Saved formulas",
    "Référentiel nutritionnel et prix": "Nutritional reference data and prices",
    "Alertes": "Alerts",
    "Utilisateur": "User",
    "Assistant": "Assistant",
    "Outil métier": "Business tool",
    "Système": "System",
    # --- Noms d'objets (« Suppression impossible : … (x, y) », verbose_name_plural) -------------------------
    "utilisateurs": "users",
    "sources documentaires": "source documents",
    "historique des validations": "validation history",
    "historique des importations": "import history",
    "journal d'activité": "activity log",
    "exploitations": "farms",
    "membres d'exploitation": "farm members",
    "espèces": "species",
    "races": "breeds",
    "catégories d'animaux": "animal categories",
    "stades physiologiques": "physiological stages",
    "objectifs de production": "production objectives",
    "lots": "groups",
    "animaux": "animals",
    "observations": "observations",
    "systèmes nutritionnels": "nutrition systems",
    "nutriments": "nutrients",
    "catégories d'ingrédients": "ingredient categories",
    "ingrédients": "ingredients",
    "compositions nutritionnelles": "nutritional compositions",
    "compositions": "compositions",
    "prix des ingrédients": "ingredient prices",
    "références nutritionnelles": "nutritional references",
    "besoins nutritionnels": "nutritional requirements",
    "contraintes d'incorporation": "inclusion constraints",
    "formules": "formulas",
    "ingrédients de la formule": "formula ingredients",
    "rations": "rations",
    "historique alimentaire": "feeding history",
    "pesées": "weighings",
    "plages de suivi de croissance": "growth monitoring ranges",
    "plages de suivi": "monitoring ranges",
    "règles d'alerte": "alert rules",
    "alertes": "alerts",
    "documents techniques": "technical documents",
    "passages": "passages",
    "conversations IA": "AI conversations",
    "messages IA": "AI messages",
}

# Fin de l'avertissement des alertes de croissance (alerts.engine.NOT_A_DIAGNOSIS), repris dans les motifs.
_NOT_A_DIAGNOSIS = (
    r"Cette alerte signale un écart par rapport à une plage de suivi ; ce n'est pas un diagnostic "
    r"vétérinaire\. "
    r"En cas de doute sur la santé de l'animal, consultez un vétérinaire\."
)
_NOT_A_DIAGNOSIS_EN = (
    "This alert flags a deviation from a monitoring range; it is not a veterinary diagnosis. "
    "If in doubt about the animal's health, consult a veterinarian."
)
_GROWTH = (
    r"GMD de (?P<adg>\S+) g/j entre le (?P<start>\S+) et le (?P<end>\S+), {direction} à la plage "
    r"« (?P<range>.+?) » \((?P<low>\S+) à (?P<high>\S+) g/j ; source : (?P<source>.+)\)\. " + _NOT_A_DIAGNOSIS
)
_GROWTH_EN = (
    "ADG of {{adg}} g/d between {{start}} and {{end}}, {direction} the range “{{range}}” "
    "({{low}} to {{high}} g/d; source: {{source}}). " + _NOT_A_DIAGNOSIS_EN
)

PATTERNS = [
    # --- Erreurs génériques ---------------------------------------------------------------------------------
    (
        r"Suppression impossible : cet élément est encore utilisé \((?P<what>.+)\)\.",
        "Cannot delete: this item is still in use ({what}).",
    ),
    (r"Valeur non autorisée \(règle « (?P<rule>.+) »\)\.", "Value not allowed (rule “{rule}”)."),
    (
        r"Action impossible depuis le statut « (?P<status>.+) »\.",
        "Action not possible from the “{status}” status.",
    ),
    # --- Moteur de formulation : avertissements et refus ----------------------------------------------------
    (r"« (?P<name>.+?) » exclu : (?P<why>.+)\.", "“{name}” excluded: {why}."),
    (
        r"valeur\(s\) validée\(s\) inconnue\(s\) pour : (?P<codes>[^;]+)",
        "validated value(s) unknown for: {codes}",
    ),
    (r"Le prix de « (?P<name>.+) » est une donnée DEMO\.", "The price of “{name}” is DEMO data."),
    (
        r"Prix de « (?P<name>.+) » saisi pour ce calcul \((?P<price>\S+) par kg brut\)\.",
        "Price of “{name}” entered for this calculation ({price} per kg as fed).",
    ),
    (
        r"Référence retenue automatiquement : « (?P<name>.+) »\.",
        "Reference selected automatically: “{name}”.",
    ),
    (
        r"Le solveur n'a pas abouti \(statut : (?P<status>.+)\)\.",
        "The solver did not reach a result (status: {status}).",
    ),
    (
        r"Minimum de (?P<bound>\S+) (?P<unit>.+?) impossible à atteindre : il manque environ (?P<gap>\S+) "
        r"(?P=unit)\.",
        "Minimum of {bound} {unit} cannot be reached: about {gap} {unit} short.",
    ),
    (
        r"Maximum de (?P<bound>\S+) (?P<unit>.+?) impossible à respecter : dépassement d'environ "
        r"(?P<gap>\S+) (?P=unit)\.",
        "Maximum of {bound} {unit} cannot be respected: exceeded by about {gap} {unit}.",
    ),
    (
        r"Matière sèche de « (?P<name>.+) » inconnue \(aucune valeur validée\)\.",
        "Dry matter of “{name}” unknown (no validated value).",
    ),
    (
        r"Aucun prix enregistré pour « (?P<name>.+) » dans cette exploitation\.",
        "No price recorded for “{name}” on this farm.",
    ),
    # Libellés des contraintes
    (r"Incorporation : (?P<label>.+)", "Inclusion: {label}"),
    (r"Disponibilité : (?P<name>.+)", "Availability: {name}"),
    (r"(?P<code>[^()]+) \(apport journalier\)", "{code} (daily supply)"),
    (r"(?P<code>[^()]+) \(teneur de la ration\)", "{code} (ration content)"),
    (r"(?P<code>[^()]+) \(teneur\)", "{code} (content)"),
    # Unités
    (r"(?P<unit>[^\s/]+)/jour", "{unit}/day"),
    (r"(?P<unit>[^\s/]+)/kg MS", "{unit}/kg DM"),
    (r"(?P<unit>[^\s/]+)/kg brut", "{unit}/kg as fed"),
    # Nutriment avec son unité : « MAT (g/kg MS) ».
    (r"(?P<code>[^()]+) \((?P<unit>[^()\s]+/kg (?:MS|brut))\)", "{code} ({unit})"),
    (
        r"(?P<target>.+) : (?P<low>[\d.]+) – (?P<high>[\d.]+) % MS",
        "{target}: {low} – {high} % DM",
    ),
    (
        r"Le nutriment (?P<code>\S+) appartient au système « (?P<system>.+?) », incompatible avec la "
        r"référence "
        r"exprimée dans « (?P<ref>.+) »\.",
        "Nutrient {code} belongs to the “{system}” system, incompatible with the reference expressed in "
        "“{ref}”.",
    ),
    (
        r"Teneur en matière sèche invalide : (?P<dm>\S+) g/kg \(attendu : 0 < MS ≤ 1000\)\.",
        "Invalid dry matter content: {dm} g/kg (expected: 0 < DM ≤ 1000).",
    ),
    (
        r"La borne maximale \((?P<label>.+)\) doit être ≥ à la borne minimale\.",
        "The maximum bound ({label}) must be ≥ the minimum bound.",
    ),
    (
        r"« (?P<name>.+) » est un ingrédient d'une autre exploitation\.",
        "“{name}” is an ingredient from another farm.",
    ),
    # --- Profil d'un lot (animals.services.group_profile) et historique d'un animal -------------------------
    (
        r"Le lot « (?P<name>.+) » ne compte aucun animal présent\.",
        "Group “{name}” has no animals present.",
    ),
    (
        r"Lot mixte, (?P<label>[^:]+) : valeur la plus fréquente retenue \((?P<value>.+), (?P<count>\d+) "
        r"animaux "
        r"sur (?P<total>\d+)\)\.",
        "Mixed group, {label}: most frequent value used ({value}, {count} animals out of {total}).",
    ),
    (
        r"Poids moyen du lot : (?P<weight>\S+) kg \((?P<weighed>\d+) animal\(aux\) pesé\(s\) sur "
        r"(?P<total>\d+)\)\.",
        "Average group weight: {weight} kg ({weighed} animal(s) weighed out of {total}).",
    ),
    (r"Pesée : (?P<weight>\S+) kg", "Weighing: {weight} kg"),
    (r"Observation \((?P<kind>.+)\)", "Observation ({kind})"),
    (r"Ration « (?P<name>.+) » \((?P<status>[^()]+)\)", "Ration “{name}” ({status})"),
    (r"Distribution : (?P<qty>\S+) kg \((?P<consumed>.+)\)", "Feeding: {qty} kg ({consumed})"),
    (r"(?P<qty>\S+) kg consommés", "{qty} kg consumed"),
    # --- Alertes (titres et messages enregistrés) -----------------------------------------------------------
    (r"Pesée à prévoir : (?P<animal>.+)", "Weighing due: {animal}"),
    (r"Dernière pesée le (?P<date>\S+)", "Last weighing on {date}"),
    (
        r"Aucune pesée depuis l'enregistrement \((?P<date>\S+)\)",
        "No weighing since registration ({date})",
    ),
    (
        r"(?P<since>.+), soit il y a (?P<days>\d+) jours\. Intervalle de suivi configuré : "
        r"(?P<interval>\d+) jours\.",
        "{since}, i.e. {days} days ago. Configured monitoring interval: {interval} days.",
    ),
    (r"Informations à compléter : (?P<animal>.+)", "Information to complete: {animal}"),
    (
        r"Informations manquantes : (?P<missing>.+)\. Elles sont nécessaires au suivi de croissance et au "
        r"choix "
        r"d'une référence nutritionnelle\.",
        "Missing information: {missing}. It is needed for growth monitoring and for choosing a nutritional "
        "reference.",
    ),
    (r"Croissance hors plage de suivi : (?P<animal>.+)", "Growth outside monitoring range: {animal}"),
    (_GROWTH.format(direction="inférieur"), _GROWTH_EN.format(direction="below")),
    (_GROWTH.format(direction="supérieur"), _GROWTH_EN.format(direction="above")),
    (r"Suivi alimentaire à compléter : (?P<ration>.+)", "Feeding records to complete: {ration}"),
    (r"dernière distribution enregistrée le (?P<date>\S+)", "last feeding recorded on {date}"),
    (
        r"Ration en cours, (?P<since>.+?) \((?P<days>\d+) jours\)\. Délai de suivi configuré : "
        r"(?P<delay>\d+) jours\.",
        "Ongoing ration, {since} ({days} days). Configured follow-up delay: {delay} days.",
    ),
    (
        r"Formule en attente de vérification : (?P<name>.+)",
        "Formula awaiting expert review: {name}",
    ),
    (
        r"(?P<total>\d+) donnée\(s\) de référence en attente de validation",
        "{total} reference data item(s) awaiting validation",
    ),
    (
        r"En attente : (?P<detail>.+)\. Elles ne sont pas utilisées dans les calculs tant qu'elles ne sont "
        r"pas "
        r"validées\.",
        "Pending: {detail}. They are not used in calculations until they are validated.",
    ),
    (
        r"(?P<count>\d+) (?P<label>ingrédients|compositions|références nutritionnelles|contraintes "
        r"d'incorporation"
        r"|plages de suivi|documents techniques)",
        "{count} {label}",
    ),
    (r"Paramètre\(s\) inconnu\(s\) : (?P<names>.+)\.", "Unknown parameter(s): {names}."),
    (r"(?P<label>.+) : nombre entier attendu\.", "{label}: whole number expected."),
    (
        r"(?P<label>.+) : valeur entre (?P<low>\S+) et (?P<high>\S+) attendue\.",
        "{label}: value between {low} and {high} expected.",
    ),
    # --- Imports CSV ----------------------------------------------------------------------------------------
    (r"Colonnes obligatoires absentes : (?P<columns>.+)\.", "Required columns missing: {columns}."),
    (r"Trop de lignes \((?P<max>\d+) maximum\)\.", "Too many rows ({max} maximum)."),
    (
        r"(?P<field>\S+) : « (?P<value>.*) » n'est pas un nombre valide\.",
        "{field}: “{value}” is not a valid number.",
    ),
    (
        r"date_naissance : « (?P<value>.*) » \(formats acceptés : AAAA-MM-JJ ou JJ/MM/AAAA\)\.",
        "date_naissance: “{value}” (accepted formats: YYYY-MM-DD or DD/MM/YYYY).",
    ),
    (
        r"(?P<field>\S+) : « (?P<value>.*) » inconnu pour l'espèce (?P<species>.+)\.",
        "{field}: “{value}” unknown for species {species}.",
    ),
    (
        r"race : « (?P<value>.*) » inconnue pour l'espèce (?P<species>.+)\.",
        "race: “{value}” unknown for species {species}.",
    ),
    (r"espece : code « (?P<code>.*) » inconnu\.", "espece: unknown code “{code}”."),
    (
        r"nutriment : « (?P<label>.+) » inconnu\. Vérifiez le code et le système\.",
        "nutriment: “{label}” unknown. Check the code and the system.",
    ),
    # --- Base documentaire ----------------------------------------------------------------------------------
    (
        r"Ce fichier a déjà été importé \(« (?P<title>.+) »\)\.",
        "This file has already been imported (“{title}”).",
    ),
    (
        r"Document trop long \((?P<pages>\d+) pages ; (?P<max>\d+) maximum\)\.",
        "Document too long ({pages} pages; {max} maximum).",
    ),
    (
        r"Embeddings non calculés \((?P<error>.+)\) : recherche plein texte uniquement pour ce document\.",
        "Embeddings not calculated ({error}): full-text search only for this document.",
    ),
    (
        r"Recherche sémantique indisponible \((?P<error>.+)\) : recherche plein texte\.",
        "Semantic search unavailable ({error}): full-text search.",
    ),
    (
        r"Fournisseur d'embeddings injoignable \((?P<error>.+)\)\.",
        "Embedding provider cannot be reached ({error}).",
    ),
    (
        r"Le fournisseur d'embeddings a répondu (?P<status>\S+)\.",
        "The embedding provider responded {status}.",
    ),
    (
        r"Fournisseur d'embeddings inconnu : « (?P<provider>.+) »\.",
        "Unknown embedding provider: “{provider}”.",
    ),
    # --- Assistant IA ---------------------------------------------------------------------------------------
    (
        r"Le fournisseur d'IA a répondu une erreur \((?P<status>.+)\)\.",
        "The AI provider returned an error ({status}).",
    ),
    (r"Fournisseur LLM inconnu : « (?P<provider>.+) »\.", "Unknown LLM provider: “{provider}”."),
    (r"Pesées de l'animal (?P<tag>.+)", "Weighings of animal {tag}"),
    (r"Moteur nutritionnel — formule « (?P<name>.+) »", "Nutrition engine — formula “{name}”"),
    # --- Motifs génériques : en dernier ---------------------------------------------------------------------
    # Journal d'activité : « Lot : création »…
    (r"(?P<obj>[^:]+) : (?P<verb>création|modification|suppression)", "{obj}: {verb}"),
    # Erreur d'une ligne importée : « champ : message » (le message est traduit s'il figure au catalogue).
    (r"(?P<field>[a-z_]+) : (?P<message>.+)", "{field}: {message}"),
    # Plusieurs phrases accolées (motifs de blocage d'une validation…) : traduites une à une.
    (r"(?P<first>[^.]+\.) (?P<rest>[A-ZÀ-Ý][^\n]*\.)", "{first} {rest}"),
]
