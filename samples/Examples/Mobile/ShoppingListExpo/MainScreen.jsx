// (c) 2026 Musoftware - https://musoftwares.com - MIT License
// MainScreen - the list.  Shows: a React Native (Expo) app designed in RAD IDE's phone designer, a text field
// + button, MListView rows (icon|title|subtitle), a Switch filter, a Timer that refreshes the list after the item
// screen changed it, ShowForm(name, args) navigation, Toast / MsgBox / Confirm dialogs.
import { MainScreenDesigner } from './MainScreen_designer';
import { RadApp } from './radapp';
import { addItem, removeBought, rows, store, summary } from './store';

export default class MainScreen extends MainScreenDesigner {
  MainScreen_Load(e) {
    this.shown = -1;
    this.visible = [];
    ['Milk', 'Bread', 'Tomatoes'].forEach(addItem);
    this.refresh();
  }

  refresh() {
    const list = rows(this.swHideBought.Checked);
    this.visible = list.map((r) => r.index);
    this.lstItems.SetItems(list.map((r) => r.row));
    this.lblSummary.Text = summary();
    this.shown = store.version;
  }

  btnAdd_Click(e) {
    const msg = addItem(this.txtItem.Text);
    if (msg) this.Toast(msg);
    this.txtItem.Text = '';
    this.refresh();
  }

  lstItems_Tap(e) {
    this.ShowForm('ItemScreen', this.visible[e.Index]);
  }

  swHideBought_Changed(e) {
    this.refresh();
  }

  async btnClearBought_Click(e) {
    if (!store.items.some((i) => i.bought)) { this.Toast('Nothing is marked as bought'); return; }
    if (await this.Confirm('Remove all bought items?')) {
      this.Toast(`Removed ${removeBought()} items`);
      this.refresh();
    }
  }

  tmrRefresh_Tick(e) {
    if (store.version !== this.shown) this.refresh();     // the item screen changed something
  }

  AppBar1_Click(e) {
    this.MsgBox('A shopping list made with RAD IDE and React Native (Expo).', 'About');
  }
}
