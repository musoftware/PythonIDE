// Runs the generated Variants_Expo screen in Node (bundled by Variants/Targets/check_targets.py with stubs.js)
import Form1 from '../../../Variants/Targets/Variants_Expo/Form1.jsx';

function find(node, pred, out = []) {
  if (!node || typeof node !== 'object') return out;
  if (Array.isArray(node)) { node.forEach((n) => find(n, pred, out)); return out; }
  if (pred(node)) out.push(node);
  (node.children || []).forEach((n) => find(n, pred, out));
  if (node.props && node.props.children) find(node.props.children, pred, out);
  return out;
}
const out = {};
function look(tag, w, h) {
  globalThis.WIN_W = w; globalThis.WIN_H = h;
  const f = new Form1({});
  f.state.cw = w;
  const tree = f.render();
  const btn = find(tree, (n) => n.props && n.props.c === f.btnGo)[0];
  const pane = find(tree, (n) => n.props && n.props.mode !== undefined && n.props.ratio !== undefined)[0];
  out[tag] = { sizes: f.CurrentSizes, btnLeft: btn ? btn.props.style.left : null, text: f.btnGo.Text,
               side: f.lblSide.Visible, pane: !!pane };
}
look('phone', 412, 867);
look('tablet', 900, 700);
console.log('RESULT ' + JSON.stringify(out));
