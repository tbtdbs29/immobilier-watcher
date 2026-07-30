from rapidfuzz import fuzz



def remove_duplicates(properties):

    unique = []


    for prop in properties:

        duplicate = False


        for saved in unique:

            score = fuzz.ratio(
                prop.title,
                saved.title
            )


            if (
                score > 85
                and
                prop.price == saved.price
            ):

                duplicate = True
                break


        if not duplicate:

            unique.append(prop)


    return unique