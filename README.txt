Goals:
 * Backward-compatible with vars not defined with the framework

Examples:
 * Set socket timeout on a per callstack basis.
 * Pass down an arg you forgot to pass deep into a stack without changing the formal params of every function on the way down.
 * Scope config vars.

Caveats:
 * Works only with globals at the moment.
 * It's impossible to hide from hasattr(). That's about the only introspection we can't paper over.