JavaScript / TypeScript

Use const by default. Use let only when a variable needs to be reassigned. Never use var.
Use async/await for all asynchronous code. Avoid raw .then() chains.
Wrap all await calls in try/catch. Never let async errors fail silently.
Use optional chaining (?.) when accessing properties that may be undefined: data?.models?.length.
Use template literals for string interpolation: `Hello ${name}` not "Hello " + name.
Do not use ==. Always use === for equality checks.
Prefer named exports over default exports for non-component files. Default exports are fine for page and component files.
If using TypeScript, define an interface or type for every API response shape. Do not use any.
