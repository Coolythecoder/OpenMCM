/** Optional MTASC-style entry point. Journal patching should call Bootstrap directly. */
class MCMCompatEntry
{
	public static function main(rootClip:MovieClip):Void
	{
		var journal:Object = _root.QuestJournalFader.Menu_mc;
		if (journal != undefined)
			MCMCompatBootstrap.install(journal);
	}
}
