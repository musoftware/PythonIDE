# Notebook_Pandas - Jupyter notebook in RAD IDE

What it shows: a Jupyter notebook (`Analysis.ipynb`) made with **File > New Notebook > Data Science Starter**
and run inside the IDE, with its outputs saved in the file:

- markdown cells (rendered), code cells with execution counts `[1]`, `[2]` ...
- pandas DataFrames shown as HTML tables (`df.head()`, `describe()`, `groupby`)
- a matplotlib plot shown inline under its cell
- an exception with its full traceback (`ZeroDivisionError`)
- a long loop cell to try **Interrupt** (not run in the saved file)

`sales.csv` is the sample data the notebook reads.

## How to try it

1. File > Open File... (or File > New Notebook > Open Notebook...) and pick `Analysis.ipynb`.
2. The kernel box (top right of the notebook) picks a Python that has `ipykernel`: a `.venv` next to the
   notebook, the IDE's own Python, or any interpreter found by **Find more kernels...** / **Browse...**.
   If the chosen Python lacks ipykernel the IDE offers to `pip install ipykernel` into it.
3. **Run All**, or run one cell with **Shift+Enter** (Ctrl+Enter = run and stay, Alt+Enter = run and insert).
   Esc leaves the editor: then A / B insert a cell above / below, D D deletes, M / Y switch markdown / code,
   Z undoes the delete, arrows move between cells.
4. Run the last cell and press **Interrupt** - you get `KeyboardInterrupt` and the kernel keeps its variables.
   **Restart** clears them (execution counts start again from 1).
5. **Notebook > Variables Window** lists `df`, `fig`, ... with type / shape; double-click `df` shows it as a table.
6. IntelliSense in cells: type `df.` or `pd.read_` (kernel completions, plus pylsp when installed).
7. **Export** > Python Script (`# %%` cells) or HTML page. Ctrl+S saves the notebook with its outputs.
