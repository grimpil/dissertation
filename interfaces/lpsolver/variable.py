#! /usr/bin/env python
# -*- coding:utf-8 -*-
# Author: Kapil Thadani (kapil@cs.columbia.edu)

from __future__ import division, with_statement
from constraint import Constraint


class Variable(object):
    """A generalized variable class for linear programs. Implementations should
    inherit from this class and also implement __slots__.
    """
    # For memory efficiency and performance, Variables make use of __slots__.
    # This means they do not have an internal __dict__, cannot be pickled
    # and do not support weak references, among other things.
    __slots__ = ['type', 'grounding', 'linked_idxs', 'raw_linked_idxs',
                 'linked_type', 'constraints', 'coeff', 'metadata']

    def __init__(self, var_type, **kwargs):
        """Initialize the default members of all variables.
        """
        # The type of the variable (to be set by subclass initalization)
        self.type = var_type

        # A dictionary for storing grounding information like external indices
        # and values; useful if this class is being instantiated directly
        # instead of subclassing.
        self.grounding = kwargs

        # Dictionaries for maintaining connections between this variable and
        # other related variables. The former maps a unique name to a list of
        # indices for the other variable and the latter maps names to the type
        # of the other variable.
        self.linked_idxs = {}
        self.linked_type = {}

        # The linked indices are generated by the combination of a raw
        # index and an external offset for this variable type. Consequently,
        # all setter methods access only the raw linked indices.
        self.raw_linked_idxs = {}

        # A list of variable-specific constraints
        self.constraints = []

        # The coefficient of the variable in the objective function
        self.coeff = 0

        # User-specified metadata
        self.metadata = None

    def is_type(self, type_str):
        """Return True if the variable is of the given type.
        """
        if self.type == type_str:
            return True
        else:
            return False

    def is_ungrounded(self):
        """Return True if the variable has no grounding information.
        """
        if len(self.grounding) == 0:
            return True
        else:
            return False

    def add_grounding(self, **kwargs):
        """Augment the grounding attributes provided at initialization.
        """
        self.grounding.update(kwargs)

    def set_coeff(self, coeff):
        """Set the coefficient of the variable.
        """
        self.coeff = coeff

    def set_idx(self, idx):
        """Set the index of the variable within the collection of variables of
        the same type.
        """
        self.raw_linked_idxs['own_idx'] = set([idx])
        self.linked_type['own_idx'] = self.type

    def idx(self):
        """Retrieve the "global" index of the variable in the linear program.
        """
        return self.linked_idxs['own_idx'][0]

    def raw_idx(self):
        """Retrieve the "local" index of the variable within the list of
        variables of this type.
        """
        return list(self.raw_linked_idxs['own_idx'])[0]

    def add_link(self, name, var):
        """Add a link from this variable to another variable by supplying a
        name and the variable to link to.
        """
        # Check if the link name is already associated with a type
        if name not in self.linked_type:
            self.linked_type[name] = var.type
        elif self.linked_type[name] != var.type:
            print "ERROR: link name", name, "in", self.type, "variable",
            print "is in use for variables of type", self.linked_type[name],
            print "and can't be assigned to a", var.type, "variable."
            print self.readable_links(raw=True)
            raise Exception

        if name not in self.raw_linked_idxs:
            self.raw_linked_idxs[name] = set([var.raw_idx()])
        else:
            self.raw_linked_idxs[name].add(var.raw_idx())

    def add_links(self, name, vars):
        """Add links from this variable to other variables by supplying a name
        and an iterable of variables to link to. This is a generalization of
        add_link() for convenience.
        """
        # Check if the link name is already associated with a type
        if name not in self.linked_type:
            self.linked_type[name] = vars[0].type
        elif self.linked_type[name] != vars[0].type:
            print "ERROR: link name", name, "in", self.type, "variable",
            print "is in use for variables of type", self.linked_type[name],
            print "and can't be assigned to a", vars[0].type, "variable."
            print self.readable_links(raw=True)
            raise Exception

        if name not in self.raw_linked_idxs:
            self.raw_linked_idxs[name] = set([var.raw_idx() for var in vars])
        else:
            self.raw_linked_idxs[name].update(var.raw_idx() for var in vars)

    def has_link(self, name):
        """Return whether the variable has a named link to any other variables.
        """
        return name in self.linked_type

    def apply_offsets(self, offsets):
        """Add offsets to all variable indices and generate externally
        accessible linked indices.
        """
        for name in self.raw_linked_idxs:
            var_type = self.linked_type[name]
            if var_type not in offsets:
                print "Unknown variable type", var_type, "in variable links"
                print self.readable_links(raw=True)
            else:
                self.linked_idxs[name] = [idx + offsets[var_type] for idx in
                                          self.raw_linked_idxs[name]]

    def readable_attribs(self):
        """Return a readable summary of the variable's core members for
        debugging purposes.
        """
        string = "%(type)s variable with coefficient %(coeff)s" % \
                {'type': self.type,
                 'coeff': self.coeff}
        return string

    def readable_links(self, raw=False):
        """Return a readable summary of the links that this variable has with
        other variables.
        """
        string = ""
        for name in self.raw_linked_idxs:
            string += "%(name)s %(type)s %(indices)s\n" % \
                        {'name': name,
                         'type': self.linked_type[name],
                         'indices': self.raw_linked_idxs[name] if raw else
                                    self.linked_idxs[name]}
        return string

    def readable_constraints(self):
        """Return a readable form of the inequality constraints on this
        variable.
        """
        string = ''
        for constraint in self.constraints:
            string += constraint.readable() + '\n'

            string_var = constraint.readable_with_var(self, only_lhs=True)
            if string_var != '':
                string += string_var + '\n'

        return string

    def readable_grounding(self):
        """Return a readable form of the grounding dictionary in this
        variable.
        """
        return ', '.join((str(key) + '=' + str(self.grounding[key])
                        for key in sorted(self.grounding.iterkeys())))

    def set_metadata(self, metadata):
        """Add some user-defined metadata to this variable, such as a list of
        feature values.
        """
        self.metadata = metadata

    def retrieve_grounding(self, *args):
        """Return a list of grounding attributes in the order of the input list
        of attribute names.
        """
        values = []
        for name in args:
            if name not in self.grounding:
                print "ERROR: unknown grounding attribute", name,
                print "for", self.type, "variable"
            else:
                values.append(self.grounding[name])

        if len(values) == 1:
            return values[0]
        else:
            return values

    def get_unique_id(self):
        """Return what should amount to a unique ID for the variable in a
        single linear program by concatenating its type and raw index. Note
        that the non-raw index after applying offsets should also be unique,
        but this is intended to work in either case.
        """
        return self.type + str(list(self.raw_linked_idxs['own_idx'])[0])

    def add_constraint(self, constraint_type, *args, **kwargs):
        """Add a constraint specifically for this variable.
        """
        getattr(self, constraint_type)(*args, **kwargs)

###############################################################################
# Constraints

    def general(self, *args, **kwargs):
        """A basic constraint; expects all standard arguments for generating an
        inequality constraint.
        """
        self.constraints.append(Constraint(*args, **kwargs))

    def iff(self, *args, **kwargs):
        """A constraint that enforces that if the (indicator) variable is
        active, all of its (indicator) links must also be active (and vice
        versa).
        """
        # X*v - Σ x = 0
        link = args[0]
        self.constraints.append(Constraint(['own_idx', link],
                                           [link, -1],
                                           '=', 0,
                                           **kwargs))

    def iff_exactly(self, *args, **kwargs):
        """A constraint that enforces that if the (indicator) variable is
        active, exactly N of its (indicator) links must also be active (and
        vice versa).
        """
        # N*v - Σ x = 0
        N, link = args
        self.constraints.append(Constraint(['own_idx', link],
                                           [N, -1],
                                           '=', 0,
                                           **kwargs))

    def implies(self, *args, **kwargs):
        """A constraint that enforces that, if the (indicator) variable is
        active, all of its (indicator) links must be active.
        """
        # X*v - Σ x <= 0
        link = args[0]
        self.constraints.append(Constraint(['own_idx', link],
                                           [link, -1],
                                           '<=', 0,
                                           **kwargs))

    def implies_at_least(self, *args, **kwargs):
        """A constraint that enforces that, if the (indicator) variable is
        active, at least N of its (indicator) links must be active.
        """
        # N*v - Σ x <= 0
        N, link = args
        self.constraints.append(Constraint(['own_idx', link],
                                           [N, -1],
                                           '<=', 0,
                                           **kwargs))

    def has_flow_over(self, *args, **kwargs):
        """A constraint that enforces single commodity flow over the variable
        and grounds whether flow is active or not based on one of its
        (indicator) links.
        """
        # v - Σ F*x <= 0
        link, max_flow = args
        self.constraints.append(Constraint(['own_idx', link],
                                           [1, -max_flow],
                                           '<=', 0,
                                           **kwargs))

        # Also set the maximum flow value as an upper bound for these variables
        self.upper_bound = max_flow

    def consumes_flow_between(self, *args, **kwargs):
        """A constraint that enforces flow consumption from connected flow
        variables, thereby ensuring their connectivity in a tree structure.
        """
        # Σ x - Σ y = 1
        incoming_link, outgoing_link = args
        self.constraints.append(Constraint([incoming_link, outgoing_link],
                                           [1, -1],
                                           '=', 1,
                                           **kwargs))

    def requires_flow_between(self, *args, **kwargs):
        """A constraint that enforces flow consumption from connected flow
        variables if the current (indicator) variable is active. This doesn't
        enforce a tree structure by itself without other constraints to
        activate this variable.
        """
        # Σ x - Σ y = v
        incoming_link, outgoing_link = args
        self.constraints.append(Constraint([incoming_link, outgoing_link,
                                            'own_idx'],
                                           [1, -1, -1],
                                           '=', 0,
                                           **kwargs))