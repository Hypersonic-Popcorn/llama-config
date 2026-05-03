React

Always use functional components with hooks. Never use class components.
Every useEffect that sets up a setInterval, event listener, or subscription must return a cleanup function that tears it down.
Every useEffect must have a dependency array. An empty array [] is intentional and acceptable — a missing array is always a bug.
Use useState for any value that should cause a re-render when it changes. Never store UI state in regular variables.
Never mutate state directly. Always use the setter function from useState, and for objects/arrays, create a new copy rather than modifying in place.
Keep components focused. If a component is doing more than one distinct thing, split it.
Lift state up to the lowest common ancestor that needs it. Do not duplicate state across sibling components.
All API calls go in useEffect or event handlers, never at the top level of a component.
Always handle three states for async data: loading, error, and success. Never render as if data is always available.
Use prop destructuring in function signatures for clarity: function ModelCard({ name, status, onClick }) not function ModelCard(props).
