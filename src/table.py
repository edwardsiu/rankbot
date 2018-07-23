# -*- coding: utf-8 -*-
from math import ceil
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

def make_row(row, max_widths, column):
    columns = len(row)
    second_row_list = []
    need_second_row = False
    if column:
        row[column] = "[{}]".format(row[column])
    for i, e in enumerate(row):
        str_e = str(e)
        if len(str_e) > max_widths[i]:
            tokens = str_e.split()
            ntokens = len(tokens)
            divider = ceil(ntokens/2)
            second_row_list.append("↳ " + " ".join(tokens[divider:]))
            row[i] = " ".join(tokens[:divider])
            need_second_row = True
        else:
            second_row_list.append("")
    first_row = E_V + E_V.join(["{}".format(row[i]).ljust(max_widths[i]) for i in range(columns)]) + E_V
    if need_second_row:
        second_row = E_V + E_V.join(["{}".format(second_row_list[i]).ljust(max_widths[i]) for i in range(columns)]) + E_V
        return first_row + "\n" + second_row
    return first_row

def make_table(headings, rows, column):
    max_widths = []
    all_data = [headings]+rows
    columns = len(headings)
    for col in range(columns):
        lengths = [len(str(row[col])) for row in all_data]
        max_len = max(lengths)
        if max_len > 17:
            max_len = 17
        max_widths.append(max_len + 1)
    top_edge = C_TL + D_T.join([E_H * width for width in max_widths]) + C_TR
    header = make_row(headings, max_widths, None)
    divider = D_L + D_C.join([E_H * width for width in max_widths]) + D_R
    bottom_edge = C_BL + D_B.join([E_H * width for width in max_widths]) + C_BR
    text_rows = []
    for row in rows:
        text_rows.append(make_row(row, max_widths, column))
    table = [top_edge, header, divider] + text_rows + [bottom_edge]
    return "\n".join(table)
