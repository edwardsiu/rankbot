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
CONT = "↳ "

class Table(object):
    def __init__(self, title="", columns=None, rows=None, max_width=64, padding=1, syntax=""):
        self.title = title
        self.columns = columns
        self.rows = rows
        self.column_widths = []
        self.max_width = max_width - 1 # subtract table edge
        self.padding = padding # 1 char for a space and 1 char for a table edge
        self.syntax = syntax

    def __str__(self):
        self._compute_column_widths()
        str_header = self._make_row(self.columns)
        str_rows = [self._make_row(row) for row in self.rows]
        _rows = [
            self.syntax,
            self.title,
            self.top_edge(),
            str_header,
            self.divider()
        ] + str_rows + [
            self.bottom_edge()
        ]
        return self._code_block("\n".join(_rows))

    def _compute_column_widths(self):
        _rows = [self.columns] + self.rows
        self.column_widths = []
        for i in range(len(self.columns)):
            width = max([len(_row[i]) + self.padding for _row in _rows])
            self.column_widths.append(width)
        self._fit_columns()

    def _fit_columns(self):
        # subtract table dividers for each column
        max_content_width = self.max_width - len(self.columns)

        while sum(self.column_widths) > max_content_width:
            widest_val = max(self.column_widths)
            widest_col = self.column_widths.index(widest_val)
            current_width = sum(self.column_widths)
            if (current_width - max_content_width) < widest_val/2:
                self.column_widths[widest_col] = widest_val - (current_width - max_content_width)
            else:
                self.column_widths[widest_col] = ceil(widest_val/2)

    def top_edge(self):
        return C_TL + D_T.join([E_H * w for w in self.column_widths]) + C_TR

    def divider(self):
        return D_L  + D_C.join([E_H * w for w in self.column_widths]) + D_R

    def bottom_edge(self):
        return C_BL + D_B.join([E_H * w for w in self.column_widths]) + C_BR

    def _split_element(self, element):
        tokens = element.split()
        ntokens = len(tokens)
        divider = ceil(ntokens/2)
        elem_a = " ".join(tokens[:divider])
        elem_b = CONT + " ".join(tokens[divider:])
        return elem_a, elem_b

    def _make_row(self, row):
        ncolumns = len(row)
        row2 = [""]*ncolumns

        for i, element in enumerate(row):
            if len(element) > (self.column_widths[i] - self.padding):
                row[i], row2[i] = self._split_element(element)
        str_row1 = E_V + E_V.join(["{}".format(row[i]).ljust(self.column_widths[i]) for i in range(ncolumns)]) + E_V
        if "".join(row2):
            str_row2 = E_V + E_V.join(["{}".format(row2[i]).ljust(self.column_widths[i]) for i in range(ncolumns)]) + E_V
            return str_row1 + "\n" + str_row2
        return str_row1

    def _code_block(self, string):
        return "```{}```".format(string)