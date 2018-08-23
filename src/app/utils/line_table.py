# -*- coding: utf-8 -*-
class LineTable():
    """This type of table has no headers and is meant to display 2 or 3 columns of data"""

    def __init__(self, rows, title=None, headers=None, width=33, separator=" "):
        self.title = title
        self.headers = headers
        self.rows = rows
        self.width = width - len(separator)*(len(rows[0])-1)
        self.max_width = width
        self.rows_per_table = 20
        self.separator = separator
        self.text = self.generate()

    def _calculate_widths(self):
        column_widths = []
        columns = len(self.rows[0])
        rows = self.rows if not self.headers else [self.headers]+self.rows
        for i in range(columns):
            max_width = max([len(row[i]) for row in rows])
            column_widths.append(max_width)
        total_width = sum(column_widths)
        if total_width > self.width:
            widest = column_widths.index(max(column_widths))
            if column_widths[widest] > (total_width - self.width):
                column_widths[widest] -= (total_width - self.width)
            else:
                # handle case where its not wide enough
                pass
        return column_widths

    def _truncate_cell(self, cell, width):
        return f"{cell[:width-3]}..."

    def generate(self):
        column_widths = self._calculate_widths()
        str_rows = []
        columns = len(column_widths)
        for row in self.rows:
            # truncate any cells that are too long
            for i in range(columns):
                if len(row[i]) > column_widths[i]:
                    row[i] = self._truncate_cell(row[i], column_widths[i])
            str_rows.append(self.separator.join([f"{row[i]}".ljust(column_widths[i]) for i in range(columns)]))
        if self.headers:
            hrow = self.separator.join([f"{self.headers[i]}".ljust(column_widths[i]) for i in range(columns)])
        _tables = []
        divider = "-"*len(str_rows[0])
        for i in range(0, len(self.rows), rows_per_table):
            start = i
            end = i + self.rows_per_table
            _table = "\n".join([f"`{row}`" for row in str_rows[start:end]])
            if self.headers:
                _table = f"`{hrow}`\n{_table}"
            _table = f"`{divider}`\n{_table}"
            if self.title:
                _table = f"**{self.title}**\n{_table}"
            _tables.append(_table)
        return _tables

class BlockTable(LineTable):
    def generate(self):
        column_widths = self._calculate_widths()
        str_rows = []
        columns = len(column_widths)
        for row in self.rows:
            # truncate any cells that are too long
            for i in range(columns):
                if len(row[i]) > column_widths[i]:
                    row[i] = self._truncate_cell(row[i], column_widths[i])
            str_rows.append(self.separator.join([f"{row[i]}".ljust(column_widths[i]) for i in range(columns)]))
        if self.headers:
            hrow = self.separator.join([f"{self.headers[i]}".ljust(column_widths[i]) for i in range(columns)])
        _tables = []
        divider = "-"*len(str_rows[0])
        for i in range(0, len(self.rows), rows_per_table):
            start = i
            end = i + self.rows_per_table
            _table = "\n".join([f"{row}" for row in str_rows[start:end]])
            if self.headers:
                _table = f"{hrow}\n{_table}"
            _table = f"{divider}\n{_table}"
            if self.title:
                _table = f"**{self.title}**\n{_table}"
            _tables.append(f"```{_table}```")
        return _tables
