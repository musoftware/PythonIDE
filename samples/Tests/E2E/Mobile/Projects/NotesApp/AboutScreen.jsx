// AboutScreen - Arabic page (written in the RAD IDE code editor).
import { AboutScreenDesigner } from './AboutScreen_designer';
import { RadApp } from './radapp';

export default class AboutScreen extends AboutScreenDesigner {
  AboutScreen_Load(e) {
  }

  btnBack_Click(e) {
    this.CloseForm();
  }
}
