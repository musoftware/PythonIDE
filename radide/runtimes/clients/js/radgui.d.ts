// RAD IDE - type declarations for the GUI Bridge globals (JavaScript / TypeScript).
// Copied into the project so editors and `tsc --noEmit` know the API.

/** Event arguments (mouse/key events; zeros otherwise). */
interface RadEvent {
  X: number; Y: number; Button: number; KeyCode: number; KeyChar: string; args: string;
}

type RadValue = null | boolean | number | string | RadValue[] | { [key: string]: RadValue };

/** Set a property: set("lblOut", "Caption", "Hello"). */
declare function set(obj: string, prop: string, value: unknown): void;
/** Read a property as text: get("txtA", "Text"). */
declare function get(obj: string, prop: string): string;
/** Read a property as a number (0 when it is not numeric). */
declare function getNum(obj: string, prop: string): number;
/** Call a method: call("lstLog", "AddItem", "text"). Returns the answer as text. */
declare function call(obj: string, method: string, ...args: unknown[]): string;
declare function msgbox(text: unknown): string;
declare function input(prompt: string): string;
declare function show(form: string): void;
declare function hide(form: string): void;
/** Quit the program. */
declare function end(): void;
/** ui.txtA.Text, ui.lblOut.Caption = "x", ui.lstLog.AddItem("x"). */
declare const ui: { [control: string]: any };
/** Call a function of any project module (any language): radcall("Helpers.add", 2, 3). */
declare function radcall(name: string, ...args: RadValue[]): any;
declare function require(name: string): any;
