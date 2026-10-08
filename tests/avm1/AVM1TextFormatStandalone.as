/** Standalone compilation includes the utility; host injection preserves it. */
class AVM1TextFormatStandalone
{
    public static function main(root:MovieClip):Void
    {
        root.textFixtureUtil = MCMCompatUtil;
        AVM1TextFormatFixture.start(root);
    }
}
