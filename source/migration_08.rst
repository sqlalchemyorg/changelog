.. migrationlog::
    :version: 0.8

    .. migration::
        :tags: New Features, orm, configuration
        :tickets: 2058, 610
        :title: Rewritten relationship() Mechanics

      0.8 features a much improved and capable system regarding how ``relationship()`` determines
      how to join between two entities.  The new system includes these features:

      * The ``primaryjoin`` argument is **no longer needed** when constructing a ``relationship()``
        against a class that has multiple foreign key paths to the target.  Only the ``foreign_keys``
        argument is needed to specify those columns which should be included::

            class Parent(Base):
                __tablename__ = 'parent'
                id = Column(Integer, primary_key=True)
                child_id_one = Column(Integer, ForeignKey('child.id'))
                child_id_two = Column(Integer, ForeignKey('child.id'))

                child_one = relationship("Child", foreign_keys=child_id_one)
                child_two = relationship("Child", foreign_keys=child_id_two)

            class Child(Base):
                __tablename__ = 'child'
                id = Column(Integer, primary_key=True)

      * relationships against self-referential, composite foreign keys where **a column points to itself**
        are now supported.   The canonical case is as follows::

            class Folder(Base):
                __tablename__ = 'folder'
                __table_args__ = (
                  ForeignKeyConstraint(
                      ['account_id', 'parent_id'],
                      ['folder.account_id', 'folder.folder_id']),
                )

                account_id = Column(Integer, primary_key=True)
                folder_id = Column(Integer, primary_key=True)
                parent_id = Column(Integer)
                name = Column(String)

                parent_folder = relationship("Folder",
                                    backref="child_folders",
                                    remote_side=[account_id, folder_id]
                              )

      * Above, the ``Folder`` refers to its parent ``Folder`` joining from ``account_id``
        to itself, and ``parent_id`` to ``folder_id``.  When SQLAlchemy constructs an auto-join,
        no longer can it assume all columns on the "remote" side are aliased, and all columns
        on the "local" side are not - the ``account_id`` column is **on both sides**.   So the
        internal relationship mechanics were totally rewritten to support an entirely different
        system whereby two copies of ``account_id`` are generated, each containing different ''annotations''
        to determine their role within the statement.  Note the join condition within a basic eager load::

            SELECT
                folder.account_id AS folder_account_id,
                folder.folder_id AS folder_folder_id,
                folder.parent_id AS folder_parent_id,
                folder.name AS folder_name,
                folder_1.account_id AS folder_1_account_id,
                folder_1.folder_id AS folder_1_folder_id,
                folder_1.parent_id AS folder_1_parent_id,
                folder_1.name AS folder_1_name
            FROM folder
                LEFT OUTER JOIN folder AS folder_1
                ON
                    folder_1.account_id = folder.account_id
                    AND folder.folder_id = folder_1.parent_id

            WHERE folder.folder_id = ? AND folder.account_id = ?

        Thanks to the new relationship mechanics, new **annotation** functions are provided
        which can be used to create ``primaryjoin`` conditions involving any kind of SQL function, CAST,
        or other construct that wraps the target column.  Previously, a semi-public argument
        ``_local_remote_pairs`` would be used to tell ``relationship()`` unambiguously what columns
        should be considered as corresponding to the mapping - the annotations make the point
        more directly, such as below where ``Parent`` joins to ``Child`` by matching the
        ``Parent.name`` column converted to lower case to that of the ``Child.name_upper`` column::

            class Parent(Base):
                __tablename__ = 'parent'
                id = Column(Integer, primary_key=True)
                name = Column(String)
                children = relationship("Child",
                        primaryjoin="Parent.name==foreign(func.lower(Child.name_upper))"
                    )

            class Child(Base):
                __tablename__ = 'child'
                id = Column(Integer, primary_key=True)
                name_upper = Column(String)


    .. migration::
        :tags: Removed, general
        :tickets: 2433
        :title: sqlalchemy.exceptions (has been sqlalchemy.exc for years)

        We had left in an alias ``sqlalchemy.exceptions`` to attempt to make it slightly easier for some
        very old libraries that hadn't yet been upgraded to use ``sqlalchemy.exc``.  Some users are still
        being confused by it however so in 0.8 we're taking it out entirely to eliminate any of that
        confusion.

