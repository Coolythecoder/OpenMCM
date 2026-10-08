/** Standalone entry point; shared probe can also run in the packaged Journal. */
class AVM1InteractionFixture
{
    public static function main(root:MovieClip):Void
    {
        AVM1InteractionProbe.prepare(root);
        var fader:MovieClip = root.createEmptyMovieClip("ConfigPanelFader", 1);
        var panel:Object = fader.createEmptyMovieClip("configPanel", 1);
        MCMCompatPanel.install(MovieClip(panel), {});
        AVM1InteractionProbe.attach(panel, false);
    }
}
