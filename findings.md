# Findings

- `app_runtime_error.log` contains repeated Gradio postprocessing failures at `hash_file(file_path)` where `file_path == D:\Desktop\归档`.
- `btn_clear` outputs to `img_input`, which is `gr.Image(type="filepath")`.
- Its callback currently returns `""` as the first tuple item. On Windows, Gradio treats this as a path; the empty path resolves to the process working directory and Gradio attempts to open the directory as a file.
- The failed clear event leaves the image component/client event chain in an error state, explaining why the next upload appears unavailable or unclickable.
- Correct empty value for a Gradio image component is `None`.
