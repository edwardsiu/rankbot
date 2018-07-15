# -*- coding: utf-8 -*-
E_H = "═"
E_V = "║"
C_TL = "╔"
C_TR = "╗"
C_BL = "╚"
C_BR = "╝"
D_T = "╦"
D_L = "╠"
D_R = "╣"
D_B = "╩"
D_C = "╬"

def make_row(row, max_widths):
    columns = len(row)
    return E_V + E_V.join(["{}".format(row[i]).ljust(max_widths[i]) for i in range(columns)]) + E_V

def make_table(headings, rows):
    max_widths = []
    all_data = [headings]+rows
    columns = len(headings)
    for col in range(columns):
        lengths = [len(str(row[col])) for row in all_data]
        max_widths.append(max(lengths) + 1)
    top_edge = C_TL + D_T.join([E_H * width for width in max_widths]) + C_TR
    header = make_row(headings, max_widths)
    divider = D_L + D_C.join([E_H * width for width in max_widths]) + D_R
    bottom_edge = C_BL + D_B.join([E_H * width for width in max_widths]) + C_BR
    text_rows = []
    for row in rows:
        text_rows.append(make_row(row, max_widths))
    table = [top_edge, header, divider] + text_rows + [bottom_edge]
    return "\n".join(table)