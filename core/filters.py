from models.property import Property



def filter_property(
    prop: Property,
    config: dict
):

    search = config["search"]


    if prop.price:

        if prop.price > search["max_price"]:
            return False


    if prop.rooms:

        if prop.rooms < search["min_rooms"]:
            return False


    if prop.property_type not in config["property"]["allowed_types"]:
        return False


    if prop.dpe:

        if prop.dpe not in config["energy"]["allowed_dpe"]:
            return False


    text = (
        prop.title
        .lower()
    )


    for word in config["property"]["exclude_keywords"]:

        if word in text:
            return False


    return True