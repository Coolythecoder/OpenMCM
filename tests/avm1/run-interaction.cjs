// All UI actions below use real browser input. ExternalInterface only supplies
// provider data and reads state; it never invokes an input callback.
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

module.exports = async function runInteraction(page, output, prefix, {reentry = false} = {}) {
  const snapshots = [];
  const call = (name, arg) => page.evaluate(({name,arg}) =>
    window.fixturePlayer.ruffle().callExternalInterface(name, arg), {name,arg});
  const snapshot = async phase => {
    const data = await call('flowSnapshot');
    snapshots.push({phase, data});
    return data;
  };
  const respond = async action => {
    await call('flowRespond', action);
    await page.waitForTimeout(120);
    return snapshot(action);
  };
  const events = () => page.evaluate(() => window.events);
  const matching = async name => (await events()).filter(e => e.kind === 'modEvent' && e.data.name === name && e.data.num >= 0);
  const row = (state, list, index) => {
    const found = state[list].rows.find(row => row.visible && row.index === index);
    assert.ok(found, `No visible ${list} entry ${index}`);
    return found;
  };
  const point = bounds => ({x:(bounds.xMin + bounds.xMax) / 2, y:(bounds.yMin + bounds.yMax) / 2});
  const rowPoint = (state, list, index) => { const r = row(state,list,index); return point(r.triggerBounds || r.bounds); };
  const click = async ({x,y}) => {
    await page.mouse.move(x,y);
    await page.waitForTimeout(100);
    if (reentry) {
      // Explicit, separately reported emulator diagnostic: Ruffle may emit
      // focus-generated rollout despite disableFocusRolloverEvent. Physical
      // re-entry permits downstream event tests without replacing handlers.
      await page.mouse.move(1200,650);
      await page.waitForTimeout(80);
      await page.mouse.move(x,y);
      await page.waitForTimeout(100);
    }
    await page.mouse.click(x,y);
    await page.waitForTimeout(140);
  };
  const clickRow = (state, list, index) => click(rowPoint(state,list,index));
  const clickControl = async name => {
    const control = await call('flowControl', name);
    assert.ok(control, `Missing modal control ${name}`);
    await click(point(control.bounds));
  };
  const assertNoNewEvents = async (name, previous) => assert.equal((await matching(name)).length, previous, `Unexpected ${name}`);

  try {
    let state = await snapshot('initial');
    assert.ok(state.modList && state.pageList && state.optionsList, 'Three independent list controls required');
    const tokens = [state.modList.token, state.pageList.token, state.optionsList.token];
    assert.equal(new Set(tokens).size, 3, 'List owners must be distinct');
    const alpha = row(state, 'modList', 0);
    assert.equal(alpha.hitAreaAssigned, false, 'Use normal transparent row geometry, not hidden hitArea');
    assert.equal(alpha.triggerVisible, true);
    assert.equal(alpha.triggerAlpha, 0, 'Authored-style trigger stays visible with an alpha-zero transform');
    const pointer = rowPoint(state,'modList',0);
    await page.mouse.move(1200,650);
    await page.mouse.move(pointer.x,pointer.y);
    await page.waitForTimeout(140);
    state = await snapshot('hoverAlpha');
    assert.equal(row(state,'modList',0).token, alpha.token, 'Hover destroyed the eventual click target');
    assert.equal(state.modList.selectedRegistryIndex, 2, 'Sorted label must retain sparse registration identity');
    assert.equal(state.focus, state.modList.path, 'Mouse selection should focus its list control');
    await click(pointer);
    state = await snapshot('clickedAlpha');
    assert.equal(state.state, 1);
    assert.equal(state.selectedMod, 2);
    assert.deepEqual((await matching('SKICP_modSelected')).map(e => e.data.num), [2]);
    const sequence = await events();
    const itemAt = sequence.findIndex(e => e.kind === 'itemPress' && e.data.registry === 2);
    const transportAt = sequence.findIndex(e => e.kind === 'modEvent' && e.data.name === 'SKICP_modSelected' && e.data.num === 2);
    assert.ok(itemAt >= 0 && transportAt > itemAt, 'Real row/list press must precede Papyrus transport');
    await click(pointer);
    await assertNoNewEvents('SKICP_modSelected',1);

    state = await respond('pages');
    assert.equal(state.modList.token,tokens[0]);
    assert.equal(state.pageList.token,tokens[1]);
    assert.equal(state.optionsList.token,tokens[2]);
    assert.equal(state.modList.visible,false);
    assert.equal(state.pageList.visible,true);
    assert.equal(state.pageList.entryCount,2, 'None is excluded without renumbering the provider page');
    await clickRow(state,'pageList',1);
    assert.deepEqual((await matching('SKICP_pageSelected')).map(e => [e.data.arg,e.data.num]), [['Styles',2]]);
    await clickRow(state,'pageList',0);
    await assertNoNewEvents('SKICP_pageSelected',1);
    state = await respond('options');
    const committedPage = state.activePage;
    state = await respond('refreshMods');
    assert.equal(state.mode,'pages', 'Registration refresh closed the active provider');
    assert.equal(state.activePage,committedPage);
    assert.equal(state.pageList.token,tokens[1]);

    await clickRow(state,'optionsList',0);
    assert.deepEqual((await matching('SKICP_optionSelected')).map(e => e.data.num), [0]);
    await clickRow(state,'optionsList',0);
    await assertNoNewEvents('SKICP_optionSelected',1);
    state = await respond('unlock');
    await clickRow(state,'optionsList',4);
    await assertNoNewEvents('SKICP_optionSelected',1);
    assert.ok(!state.optionsList.rows.some(r => r.visible && r.index === 6), 'Hidden option has a live renderer');

    await clickRow(state,'optionsList',2);
    assert.deepEqual((await matching('SKICP_sliderSelected')).map(e => e.data.num), [2]);
    state = await snapshot('sliderRequested');
    const optionsFocus = state.focus;
    state = await respond('slider');
    assert.equal(state.dialogKind,'slider');
    for (const name of ['modList','pageList','optionsList']) assert.equal(state[name].disableInput,true, name + ' did not disable input');
    assert.notEqual(state.focus,optionsFocus,'Dialog did not take focus');
    await clickRow(state,'pageList',0);
    await clickRow(state,'optionsList',0);
    await clickControl('pageBack');
    assert.equal((await snapshot('modalBackBlocked')).mode,'pages');
    await assertNoNewEvents('SKICP_pageSelected',1);
    await assertNoNewEvents('SKICP_optionSelected',1);
    const track = await call('flowControl','sliderTrack');
    const y = point(track.bounds).y;
    await page.mouse.move(620,y);
    await page.mouse.down();
    await page.mouse.move(795,y,{steps:5});
    await page.mouse.up();
    await page.waitForTimeout(140);
    assert.equal((await call('flowControl','sliderTrack')).token,track.token,'Dragging destroyed the pressed track');
    state = await snapshot('sliderDragged');
    assert.ok(state.dialogValue >= 75 && state.dialogValue <= 85);
    await clickControl('sliderAccept');
    state = await snapshot('sliderAccepted');
    assert.equal(state.dialogKind,undefined);
    assert.equal(state.focus,optionsFocus,'Dialog did not restore previous list focus');
    assert.equal((await matching('SKICP_sliderAccepted')).length,1);
    state = await respond('unlock');

    await clickRow(state,'optionsList',3);
    state = await respond('menu');
    await clickControl('menuRow2');
    state = await snapshot('menuSelected');
    assert.equal(state.dialogActive,2);
    const menuRow = row(state,'menuList',2);
    const menuPointer = rowPoint(state,'menuList',2);
    await page.mouse.move(menuPointer.x,menuPointer.y);
    await page.mouse.wheel(0,120);
    await page.waitForTimeout(180);
    state = await snapshot('menuStationaryScroll');
    assert.equal(state.menuList.scrollPosition,2);
    const reboundMenuRow = state.menuList.rows.find(r => r.token === menuRow.token);
    assert.equal(reboundMenuRow.index,4);
    assert.equal(state.menuList.selectedIndex,4);
    await page.mouse.down(); await page.mouse.up(); await page.waitForTimeout(120);
    await clickControl('menuAccept');
    assert.deepEqual((await matching('SKICP_menuAccepted')).map(e => e.data.num),[4]);
    state = await respond('unlock');

    await clickRow(state,'optionsList',7);
    state = await respond('input');
    assert.equal(state.dialogKind,'input');
    await page.keyboard.press('Control+A');
    await page.keyboard.type('Mouse and keyboard');
    await clickControl('inputAccept');
    assert.deepEqual((await matching('SKICP_inputAccepted')).map(e => e.data.arg),['Mouse and keyboard']);
    const textInput = (await events()).filter(e => e.kind === 'textInput').map(e => e.data.enabled);
    assert.deepEqual(textInput,[true,false],'Text-input ownership must balance');
    state = await respond('unlock');

    await clickRow(state,'optionsList',8);
    assert.deepEqual((await matching('SKICP_colorSelected')).map(e => e.data.num),[8]);
    state = await respond('color');
    const swatch = await call('flowControl','colorSwatch15');
    await clickControl('colorSwatch15');
    state = await snapshot('colorPicked');
    assert.equal(state.dialogColor,0xE86BA5);
    assert.equal((await call('flowControl','colorSwatch15')).token,swatch.token,'Color picking recreated its swatch');
    await clickControl('colorAccept');
    assert.deepEqual((await matching('SKICP_colorAccepted')).map(e => e.data.num),[0xE86BA5]);
    state = await respond('unlock');

    state = await respond('manyOptions');
    const optionRow = row(state,'optionsList',2);
    const optionPointer = rowPoint(state,'optionsList',2);
    await page.mouse.move(optionPointer.x,optionPointer.y);
    await page.waitForTimeout(120);
    await page.mouse.wheel(0,120);
    await page.waitForTimeout(180);
    state = await snapshot('optionStationaryScroll');
    assert.equal(state.optionsList.scrollPosition,2);
    const reboundOption = state.optionsList.rows.find(r => r.token === optionRow.token);
    assert.equal(reboundOption.index,4);
    assert.equal(state.optionsList.selectedIndex,4);
    await page.mouse.down(); await page.mouse.up(); await page.waitForTimeout(120);
    assert.equal((await matching('SKICP_optionSelected')).at(-1).data.num,4);
    state = await respond('unlock');
    await clickControl('pageBack');
    state = await snapshot('pageBack');
    assert.equal(state.mode,'mods');
    assert.equal(state.modList.selectedRegistryIndex,2);

    // Wheel input changes the contents under a stationary cursor. No mouse move
    // occurs between wheel delivery, selected-entry inspection and the click.
    state = await respond('manyMods');
    const beforeRow = row(state,'modList',1);
    const stationary = rowPoint(state,'modList',1);
    await page.mouse.move(stationary.x,stationary.y);
    await page.waitForTimeout(120);
    await page.mouse.wheel(0,120);
    await page.waitForTimeout(180);
    state = await snapshot('stationaryScroll');
    assert.ok(state.modList.scrollPosition > 0,'Wheel did not scroll the mod list');
    const now = state.modList.rows.find(r => r.token === beforeRow.token);
    assert.ok(now && now.visible && now.index > 1,'Scroll must rebind the existing row');
    assert.equal(state.modList.selectedIndex,now.index,'Stationary pointer did not reselect the new entry');
    const expectedRegistry = state.modList.selectedRegistryIndex;
    await page.mouse.down(); await page.mouse.up(); await page.waitForTimeout(120);
    assert.equal((await matching('SKICP_modSelected')).at(-1).data.num,expectedRegistry);

    state = await respond('close');
    assert.equal(state.active,false);
    state = await respond('reopen');
    assert.equal(state.modList.token,tokens[0]);
    assert.equal(state.pageList.token,tokens[1]);
    assert.equal(state.optionsList.token,tokens[2]);
    await clickRow(state,'modList',1);
    assert.equal((await matching('SKICP_modSelected')).at(-1).data.num,3,'Reopened XPMSE selected wrong registry ID');
    await page.screenshot({path:path.join(output,prefix+'after-flow.png')});
    console.log('FLOW RESULT', JSON.stringify({pass:true, emulatorReentry:reentry, snapshots:snapshots.length}));
  } finally {
    await page.screenshot({path:path.join(output,prefix+'last-state.png')});
    fs.writeFileSync(path.join(output,prefix+'events.json'),JSON.stringify({emulatorReentry:reentry,snapshots,events:await events()},null,2));
  }
};
