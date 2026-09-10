"""Phase 14 renderer integration: Unicode-aware visual runs."""
import phase5_canvas as p5
from phase14_unicode_shaping import UnicodeRunEngine, detect_shaper


def install(app):
    if getattr(app, "_pm14_installed", False): return
    app._pm14_installed=True
    app.pm14_shaper=detect_shaper()
    app.pm14_runs=lambda text: UnicodeRunEngine(app.settings.get("font","Noto Sans"), app.settings.get("size",12)).runs(text)

    # Expose diagnostics without replacing the stable Phase 13 renderer.
    def diagnostics():
        app.status.config(text=f"Unicode shaping: {app.pm14_shaper} | Unicode source preserved")
    app.pm14_diagnostics=diagnostics

_old=p5._install_app
if not getattr(_old,"_pm14_wrapped",False):
    def wrapped(app):
        _old(app); install(app)
    wrapped._pm14_wrapped=True
    p5._install_app=wrapped
