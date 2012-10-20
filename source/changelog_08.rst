==============
0.8 Changelog
==============

.. changelog::
    :version: 0.8.0b2
    :released: Oct 20, 2012

    .. change::
        :tags: bug, orm, configuration
        :tickets: 2600

      Fixed some whosiwhats thing.

.. changelog::
    :version: 0.8.0b1
    :released: Oct 12, 2012

    .. change::
        :tags: removed, general
        :tickets: 2018

      The "sqlalchemy.exceptions"
      synonym for "sqlalchemy.exc" is removed
      fully.

    .. change::
        :tags: removed, orm, configuration, changed
        :tickets: 1054

      The legacy "mutable" system of the
      ORM, including the MutableType class as well
      as the mutable=True flag on PickleType
      and postgresql.ARRAY has been removed.
      In-place mutations are detected by the ORM
      using the sqlalchemy.ext.mutable extension,
      introduced in 0.7.   The removal of MutableType
      and associated constructs removes a great
      deal of complexity from SQLAlchemy's internals.
      The approach performed poorly as it would incur
      a scan of the full contents of the Session
      when in use.

    .. change::
        :tags: feature, orm, configuration
        :tickets: 2019, 610

      Major rewrite of relationship()
      internals now allow join conditions which
      include columns pointing to themselves
      within composite foreign keys.   A new
      API for very specialized primaryjoin conditions
      is added, allowing conditions based on
      SQL functions, CAST, etc. to be handled
      by placing the annotation functions
      remote() and foreign() inline within the
      expression when necessary.  Previous recipes
      using the semi-private _local_remote_pairs
      approach can be upgraded to this new
      approach.

    .. change::
        :tags: feature, orm, querying, added
        :tickets: 2333

      New standalone function with_polymorphic()
      provides the functionality of query.with_polymorphic()
      in a standalone form.   It can be applied to any
      entity within a query, including as the target
      of a join in place of the "of_type()" modifier.

    .. change::
        :tags: feature, orm, querying
        :tickets: 2438, 1106

      The of_type() construct on attributes
      now accepts aliased() class constructs as well
      as with_polymorphic constructs, and works with
      query.join(), any(), has(), and also
      eager loaders subqueryload(), joinedload(),
      contains_eager()


    .. change::
        :tags: bug, orm, configuration
        :tickets: 2019, 610

        ORM will perform extra effort to determine
        that an FK dependency between two tables is
        not significant during flush if the tables
        are related via joined inheritance and the FK
        dependency is not part of the inherit_condition,
        saves the user a use_alter directive.
