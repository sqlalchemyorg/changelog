=============
0.7 Changelog
=============

.. changelog::
    :version: 0.7.1

    .. change::
        :tags: general

      Added a workaround for Python bug 7511 where
      failure of C extension build does not
      raise an appropriate exception on Windows 64
      bit + VC express [ticket:2184]

    .. change::
        :tags: orm
        :tickets: 1912

      "delete-orphan" cascade is now allowed on
      self-referential relationships - this since
      SQLA 0.7 no longer enforces "parent with no
      child" at the ORM level; this check is left
      up to foreign key nullability.

    .. change::
        :tags: orm
        :tickets: 2180

      Repaired new "mutable" extension to propagate
      events to subclasses correctly; don't
      create multiple event listeners for
      subclasses either.

    .. change::
        :tags: sql

      Fixed bug whereby metadata.reflect(bind)
      would close a Connection passed as a
      bind argument.  Regression from 0.6.

    .. change::
        :tags: sql

      Streamlined the process by which a Select
      determines what's in it's '.c' collection.
      Behaves identically, except that a
      raw ClauseList() passed to select([])
      (which is not a documented case anyway) will
      now be expanded into its individual column
      elements instead of being ignored.

