"""ReportViewer on the design surface: the first page of ReportFile, scaled into the control
(radide/features/report_designer.py renders it)."""
from radide.components.classic import apply_classic, prepare
from radide.features.report_designer import _viewer_preview, _viewer_props


def create(parent, props, ctx):
    return prepare(_viewer_preview(parent))


def apply(w, props, ctx):
    apply_classic(w, props, ctx, special=_viewer_props)
