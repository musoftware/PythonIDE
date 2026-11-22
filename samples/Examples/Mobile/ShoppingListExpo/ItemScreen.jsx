// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// ItemScreen - edit one item: quantity (MSlider), bought (Switch), save or delete; FormArgs = the item index.
import { ItemScreenDesigner } from './ItemScreen_designer';
import { RadApp } from './radapp';
import { removeItem, store, updateItem } from './store';

export default class ItemScreen extends ItemScreenDesigner {
  ItemScreen_Load(e) {
    const it = store.items[this.FormArgs];
    if (!it) { this.CloseForm(); return; }
    this.lblName.Text = it.name;
    this.sldQty.Value = it.qty;
    this.lblQty.Text = `Quantity: ${it.qty}`;
    this.swBought.Checked = it.bought;
  }

  sldQty_Changed(e) {
    this.lblQty.Text = `Quantity: ${Math.round(e.Value)}`;
  }

  btnSave_Click(e) {
    updateItem(this.FormArgs, { qty: Math.round(this.sldQty.Value), bought: this.swBought.Checked });
    this.CloseForm('saved');
  }

  async btnDelete_Click(e) {
    if (await this.Confirm(`Delete ${this.lblName.Text}?`)) {
      removeItem(this.FormArgs);
      this.CloseForm('deleted');
    }
  }
}
