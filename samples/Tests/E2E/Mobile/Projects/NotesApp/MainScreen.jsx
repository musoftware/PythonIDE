// MainScreen - the notes list (written in the RAD IDE code editor).
import { MainScreenDesigner } from './MainScreen_designer';
import { RadApp } from './radapp';

const KEY = 'rad-notes';
const store = globalThis.localStorage;          // web; on a phone use AsyncStorage

export default class MainScreen extends MainScreenDesigner {
  MainScreen_Load(e) {
    this.notes = JSON.parse((store && store.getItem(KEY)) || '[]');
    this.lstGreetings.Clear();
    for (const n of this.notes) this.lstGreetings.AddItem(`note|${n}`);
    this.lblHello.Text = `${this.notes.length} notes`;
  }

  btnHello_Click(e) {
    const text = this.txtName.Text.trim();
    if (!text) {
      this.Toast('Write a note first');
      return;
    }
    this.notes.push(text);
    if (store) store.setItem(KEY, JSON.stringify(this.notes));
    this.lstGreetings.AddItem(`note|${text}`);
    this.lblHello.Text = `${this.notes.length} notes`;
    this.txtName.Text = '';
  }

  lstGreetings_Tap(e) {
    this.ShowForm('DetailsScreen', this.lstGreetings.Field(e.Index, 1));
  }

  btnDetails_Click(e) {
    this.ShowForm('AboutScreen');
  }

  AppBar1_Click(e) {
    this.MsgBox('Notes - made with RAD IDE and React Native (Expo).', 'About');
  }
}
