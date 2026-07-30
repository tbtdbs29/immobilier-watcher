from models.property import Property


def filter_property(prop: Property, config: dict) -> bool:
    search = config["search"]

    # Exiger un prix valide (aucun appart ne coûte moins de 150€/mois)
    if not prop.price or prop.price < 150:
        return False

    # Vérifier la ville
    if search.get("city"):
        if not prop.city or search["city"].lower() not in prop.city.lower():
            return False

    # Prix max
    if prop.price:
        if prop.price > search["max_price"]:
            return False

    # Nombre de pièces minimum
    if prop.rooms:
        if prop.rooms < search["min_rooms"]:
            return False

    # Surface minimum
    if prop.surface:
        if prop.surface < search["min_surface"]:
            return False

    # Type de bien
    if prop.property_type not in config["property"]["allowed_types"]:
        return False

    # DPE (comparaison insensible à la casse)
    if prop.dpe:
        allowed = [d.upper() for d in config["energy"]["allowed_dpe"]]
        if prop.dpe.upper() not in allowed:
            return False

    # Mots-clés exclus
    text = prop.title.lower()
    for word in config["property"]["exclude_keywords"]:
        if word in text:
            return False

    return True