import JV, CV


def t():
    return [JV.sum(1, 2, 3), JV.join('-', 'a', 'b'), CV.Total(4, 5, 6), JV.sum()]
