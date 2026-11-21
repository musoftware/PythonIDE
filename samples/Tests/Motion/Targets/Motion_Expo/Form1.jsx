// Form1 - animations come from the Animations window (radapp.js RadFx plays them).
// this.BeginAnimation('fx1') / this.StopAnimation('fx1') / this.SetVisible('lblInfo', false)
import { Form1Designer } from './Form1_designer';
import { RadApp } from './radapp';

export default class Form1 extends Form1Designer {
  btnHide_Click(e) {
    this._hidden = !this._hidden;
    this.SetVisible('lblInfo', !this._hidden);
  }
}
