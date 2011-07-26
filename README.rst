========
stackful
========

stackful provides a variant on Lisp-style `dynamic variables`_ for Python.
They're akin to Perl’s ``local`` variables but with less tendency to degrade
into spaghetti. Use it with care, and you can quickly defeat many common cases
of coupling without having to refactor the world.

.. _`dynamic variables`: http://www.gigamonkeys.com/book/variables.html#dynamic-aka-special-variables


Introduction
------------

*“It’s hard to make predictions—especially about the future.”*—Markus
Ronner

Any software framework will inevitably have holes. There will be points of
customization you’ll wish you had, assumptions you’ll wish you hadn’t, and
chains of dependency you wish you could just poke through without the
maintenance drawbacks of globals. stackful gives you a new kind of variable
which, used prudently, lets you overcome some of the common instances of
framework shortsightedness without having to refactor your (or worse, somebody
else’s) framework.

stackful is a one-trick pony. It lets you transform a global variable into one
whose value is set on a per-call-stack basis. You can say...

::

  from stackful import stackful

  with stackful('some_global', 8):
      foo()

...and ``some_global`` will, for the extent of the ``with`` block, be converted
into a so-called “stackful” variable which has the value ``8``. That new value
will be seen only on this thread and only until the ``with`` exits: ``foo()``,
if it reads the ``some_global`` variable, will see the ``8``, as will anything
``foo()`` calls. However, other threads will continue to see the old value, if
any. When the ``with`` exits, even this thread will see the variable go back to
its original value.


What could this possibly be good for?
-------------------------------------

Globals can pass data around easily, but it's equally easy for that
cross-cutting of layers to descend into chaos. stackful lets you add temporal
limits to globals, making them easier to reason about. Here are a few examples.

Slicing singletons
==================

Let’s say you’re deep in a web application. You have a database connection
string in a global configuration variable, and you’re using a model framework
like Django 1.1’s that supports only a single database at a time. But you also
have a second database: an archival one which you still sometimes need to hit
from production. You can’t just change the global variable and then invoke your
ORM; you’ll screw up the other threads. And if you try to replace the global
with a ``threading.local()`` object, all the code that looks at it it will have
to change to get the threadlocal value out of the object. You’re stuck.

But stackful can save you! A simple transformation of the global variable to a
stackful one during the archival operations is all you need::

  from stackful import stackful

  with stackful('db', 'postgres://archival.example.com'):
      do_archival_stuff()

For the length of the ``with`` block, the whole call stack from here down sees
the ``db`` variable point to the archival database. There’s no need to pick
through the entire ORM, retrofitting every method to take a connection string
parameter. After the ``with`` exits, everything goes back to normal. And the
whole time, other threads continue to see the original value unperturbed.

Tunneling parameters
====================

It’s happened to us all—we find ourselves deep in a chain of function calls
and, at in the innermost one, find that we’re missing some bit of data. What to
do? We could change the signature of every function from here to the very top
level to make sure the needed arg is passed in, but sometimes that’s not the
best course of action. Those with a penchant for the grotesque might add a
global variable, but that’s thread-unsafe and leaves open the possibility of
forgetting to clear it when we’re done, leaking oddball parameters into the
next invocation of the innermost function.

stackful to the rescue again! By making a global, giving it some obviously
invalid value, and then making it stackful, we make forgetting to initialize it
obvious while keeping its value private to the call stack where it was set.
Here’s how it looks::

  from stackful import stackful

  rogue_param = None

  def outer():
      global rogue_param
      with stackful('rogue_param', 9):
          middle()

  def middle():
      inner()

  def inner():
      global rogue_param
      print rogue_param + 1

  outer()

The above prints ``10``. Again, everybody’s thread-safe, and once the ``with``
exits, ``rogue_param`` goes back to being ``None``.

Incidentally, we don’t do it above, but we can even stack new values on top of
the old for multiple concurrent invocations of our inner function with
different values. Just call ``stackful()`` again on the same global.


Comparison with Perl’s local variables
--------------------------------------

Our “stackful” variables are a little different in that we don’t actually
introduce any new symbols into called functions’ frames. Instead, we simply
arrange call-stack-dependent values for symbols they already reference. This
provides the useful properties of Perl’s ``local`` scoping but makes client
code easier to reason about statically.


How it works
------------

As the closest thing to an arbitrary block in Python, the ``with`` statement is
a natural fit for setting the scope of stackful variables within a lexical
scope. In the context handler implemented by ``stackful()``, we walk up to the
calling stack frame (using ``inspect``) and replace the reference to the
specified global with a special ``Proxy`` object. The main purpose of the
``Proxy`` is to make sure each thread (and thus each call stack) sees its own
separate copy of the variable. However, since Python’s ``threading.local``
object requires an attribute access to get at its threadlocal value, we need to
find a point at which to perform that access. Python gives us no way to do this
upon simply reading a module-level symbol. Perhaps we could have registered a
trace handler which examined the nearby instructions and interposed its magic
at the right moment, but I assumed that would be an unacceptable performance
hit. And code in running stack frames is immutable, so inserting cleanup
instructions was out. So, instead, we harness the fact that almost everything
you can do with a value involves operating on it, and Python lets us override
the behavior of almost every operation. ``Proxy`` overrides ``__add__``,
``__eq__``, ``__getattribute__``, and every other special method to present a
convincing front of being identical to the thread-appropriate value of the
stackful global. There are a few holes if you’re doing heavy-duty
introspection, but, in practice, it works very well.


Caveats
-------

Since this is a pure-Python implementation, there were some limits to the kinds
of lies we could tell. Here are stackful’s constraints:

* It works only with globals at the moment (which may not be such a bad thing
  from a static reasoning standpoint).
* If someone rebinds a stackful global, it will cease to be stackful; Python
  gives us no opportunity to intercept the rebinding. Thus, it's best to stick
  to read-only values and ones that get mutated in place.
* There are a few introspections we can’t paper over:

  * The ``obj is other_obj`` object identity test. Understandably, the
    interpreter goes straight to pointer comparison here for speed.
  * ``type(obj)``. There’s just no escaping this, but code should be using
    ``isinstance()`` for type testing, and other uses are pretty niche.
    ``isinstance()`` looks at ``__class__``, and we do fake that.
* I haven't even thought about wrapping old-style classes. Maybe it works, and
  maybe it doesn't.


Genesis
-------

This started as a bit of a stunt during a "hack day" at Open Source Bridge
2011. I'd found myself reaching for Lisp-style dynamic vars from time to time
for a few years and decided, more as a technical challenge than because it was
a good idea, to try hacking them onto Python. Please keep this in mind if you
decide to use stackful.


Version history
---------------

1.0
  * Initial release upon an unsuspecting world. Doubtless full of horrible
    bugs.
