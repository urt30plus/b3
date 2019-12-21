class Cursor:
    fields = None

    EOF = False

    def __init__(self, cursor, conn):
        """
        Object constructor.
        :param cursor: The opened result cursor.
        :param conn: The database connection instance.
        """
        self._cursor = cursor
        self._conn = conn
        self.rowcount = self._cursor.rowcount
        self.lastrowid = self._cursor.lastrowid
        self.fields = None
        try:
            self.EOF = self.moveNext()
        except Exception:
            # not a select statement
            self.EOF = not self.fields or self.rowcount <= 0 or not self._cursor
        if self.fields:
            self.columns = [x[0] for x in self._cursor.description]
        else:
            self.columns = None

    def moveNext(self):
        """
        Move the cursor to the next available record.
        :return True if there is one more record, False otherwise.
        """
        if not self.EOF:
            self.fields = self._cursor.fetchone()
            self.EOF = not self.fields or not self._cursor
            if self.EOF:
                self.close()
        return self.EOF

    def getOneRow(self, default=None):
        """
        Return a row from the current result set and close it.
        :return The row fetched from the result set or default if the result set is empty.
        """
        if self.EOF:
            return default
        row = self.getRow()
        self.close()
        return row

    def getRow(self):
        """
        Return a result set row into a dict.
        :return The result set row or an empty dict if there are no more records in this result set.
        """
        if self.EOF:
            return {}
        fields = self.fields
        columns = self.columns
        return dict(zip(columns, fields))

    def getValue(self, key, default=None):
        """
        Return a value from the current result set row.
        :return The value extracted from the result set or default if the the given key doesn't match any field.
        """
        return self.getRow().get(key, default)

    def close(self):
        """
        Close the active result set.
        """
        if self._cursor:
            self._cursor.close()
        self._cursor = None
        self.EOF = True

    def __iter__(self):
        while not self.EOF:
            yield self.getRow()
            self.moveNext()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __bool__(self):
        return not self.EOF
