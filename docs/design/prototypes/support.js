/*
 * Minimal preview runtime for the .dc.html prototypes in this folder.
 *
 * The prototypes were authored for the Claude Design canvas, whose runtime is
 * not part of this repo. This file implements just enough of that format to
 * render them statically in a browser:
 *   - <helmet> children move to <head>
 *   - the <script type="text/x-dc"> Component class supplies renderVals()
 *   - {{path}} holes in text and attributes, <sc-for>, <sc-if>
 *   - <dc-import name="X"> renders X.dc.html in an iframe
 * Event handlers and state are ignored: these are static comps.
 */
(function () {
  class DCLogic {
    constructor(props) {
      this.props = props || {};
      this.state = {};
    }
    setState(patch) {
      Object.assign(this.state, patch);
    }
    forceUpdate() {}
  }
  window.DCLogic = DCLogic;

  const HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;
  const WHOLE = /^\{\{\s*([^}]+?)\s*\}\}$/;

  function lookup(path, scope) {
    if (path === 'true') return true;
    if (path === 'false') return false;
    if (/^-?\d+(\.\d+)?$/.test(path)) return Number(path);
    let cur = scope;
    for (const key of path.split('.')) {
      if (cur == null) return undefined;
      cur = cur[key];
    }
    return cur;
  }

  function fill(str, scope) {
    return str.replace(HOLE, (_, p) => {
      const v = lookup(p, scope);
      return v == null ? '' : String(v);
    });
  }

  function processChildren(parent, scope) {
    for (const child of Array.from(parent.childNodes)) processNode(child, scope);
  }

  function processNode(node, scope) {
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.nodeValue.includes('{{')) node.nodeValue = fill(node.nodeValue, scope);
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const tag = node.tagName.toLowerCase();

    if (tag === 'sc-for') {
      const m = WHOLE.exec(node.getAttribute('list') || '');
      const list = m ? lookup(m[1], scope) : [];
      const as = node.getAttribute('as') || 'item';
      const frag = document.createDocumentFragment();
      (Array.isArray(list) ? list : []).forEach((item, i) => {
        const holder = document.createElement('div');
        holder.innerHTML = node.innerHTML;
        processChildren(holder, Object.assign({}, scope, { [as]: item, $index: i }));
        while (holder.firstChild) frag.appendChild(holder.firstChild);
      });
      node.replaceWith(frag);
      return;
    }

    if (tag === 'sc-if') {
      const m = WHOLE.exec(node.getAttribute('value') || '');
      if (m && lookup(m[1], scope)) {
        processChildren(node, scope);
        node.replaceWith(...Array.from(node.childNodes));
      } else {
        node.remove();
      }
      return;
    }

    if (tag === 'dc-import') {
      const frame = document.createElement('iframe');
      frame.src = node.getAttribute('name') + '.dc.html';
      const [w, h] = (node.getAttribute('hint-size') || '100%,600px').split(',');
      frame.style.cssText = 'display:block;border:0;width:' + w.trim() + ';height:' + h.trim() + ';';
      frame.setAttribute('title', node.getAttribute('name'));
      node.replaceWith(frame);
      return;
    }

    for (const attr of Array.from(node.attributes)) {
      if (!attr.value.includes('{{')) continue;
      const m = WHOLE.exec(attr.value);
      const v = m ? lookup(m[1], scope) : fill(attr.value, scope);
      if (typeof v === 'function' || v == null) node.removeAttribute(attr.name);
      else node.setAttribute(attr.name, String(v));
    }
    processChildren(node, scope);
  }

  function render() {
    const root = document.querySelector('x-dc');
    if (!root) return;
    const helmet = root.querySelector('helmet');
    if (helmet) {
      for (const el of Array.from(helmet.children)) document.head.appendChild(el);
      helmet.remove();
    }
    let vals = {};
    const script = document.querySelector('script[type="text/x-dc"]');
    if (script) {
      let props = {};
      try {
        const declared = JSON.parse(script.getAttribute('data-props') || '{}');
        for (const [k, v] of Object.entries(declared)) {
          if (!k.startsWith('$') && v && 'default' in v) props[k] = v.default;
        }
      } catch (e) {
        props = {};
      }
      const Component = new Function('DCLogic', script.textContent + '\n;return Component;')(DCLogic);
      vals = new Component(props).renderVals() || {};
    }
    processChildren(root, vals);
    root.replaceWith(...Array.from(root.childNodes));
    document.documentElement.setAttribute('data-rendered', 'true');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render);
  else render();
})();
