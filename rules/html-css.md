HTML / CSS

Never use inline styles for anything beyond truly one-off dynamic values (like a progress bar width). Appearance belongs in CSS.
Use CSS custom properties (variables) for colors, spacing, and font sizes. Define them once on :root and reference them everywhere. This makes theming consistent.
Use semantic HTML elements where appropriate: <nav> for the sidebar, <main> for page content, <header> for the top bar, <button> for clickable actions (not <div onClick>).
<button> elements should always have a type attribute: type="button" for regular buttons, type="submit" only if inside a form.
Never use <form> elements in React components. Use useState controlled inputs with onClick handlers instead.
Class names should describe what an element is, not what it looks like: model-card not blue-rounded-box.
Do not set widths or heights in pixels on layout containers. Use percentages, fr units in grid, or flexbox to let the layout breathe.
