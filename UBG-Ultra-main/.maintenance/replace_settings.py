with open(r'C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\games\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section to replace
start_marker = '<h3>Tab Cloak</h3>'
end_marker = '                </div>\n            </section>'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx)

new_content = """<h3>Theme</h3>
                        <p class="field-note">Pick an accent color — applies across every page.</p>
                        <div class="theme-swatches" id="themeSwatches"></div>
                    </div>

                    <div class="panel">
                        <h3>Background</h3>
                        <div class="field">
                            <label>Navigation bar position</label>
                            <div class="radio-group" id="navPosition">
                                <label><input type="radio" name="navPos" value="left" checked> Left</label>
                                <label><input type="radio" name="navPos" value="right"> Right</label>
                                <label><input type="radio" name="navPos" value="bottom"> Bottom</label>
                            </div>
                        </div>
                    </div>

                    <div class="panel">
                        <h3>Privacy and Cloaking</h3>
                        <div class="field">
                            <label for="cloakSelect">Tab Cloak</label>
                            <p class="field-note">Make UBG Ultra look like something harmless in your browser tab.</p>
                            <select id="cloakSelect">
                                <option value="none">Default</option>
                                <option value="google">Google</option>
                                <option value="gclassroom">Classroom</option>
                                <option value="clever">Clever</option>
                                <option value="gmail">Gmail</option>
                                <option value="gdrive">Drive</option>
                                <option value="desmos">Desmos</option>
                                <option value="wikipedia">Wikipedia</option>
                                <option value="newtab">New Tab</option>
                                <option value="bing">Bing</option>
                                <option value="custom">Custom tab title</option>
                            </select>
                        </div>
                        <div class="field" id="customCloakTitle" style="display:none">
                            <label for="cloakTitle">Custom title</label>
                            <input type="text" id="cloakTitle" placeholder="e.g. Homework Tracker" autocomplete="off" spellcheck="false">
                        </div>
                        <div class="field" id="customCloakIcon" style="display:none">
                            <label for="cloakFavicon">Custom icon URL</label>
                            <input type="text" id="cloakFavicon" placeholder="https://... or relative path" autocomplete="off" spellcheck="false">
                        </div>
                        <div class="field">
                            <label class="switch">
                                <input type="checkbox" id="autoCloak">
                                <span class="slider"></span>
                                Auto cloak — Disguise the tab only when you switch away.
                            </label>
                        </div>
                    </div>

                    <div class="panel">
                        <h3>Panic Key</h3>
                        <p class="field-note">Press your panic key anywhere to instantly redirect to a safe site.</p>
                        <div class="field">
                            <label for="panicKey">Set key: <span id="panicKeyDisplay">none</span></label>
                            <input type="text" id="panicKey" maxlength="1" placeholder="Press a key..." autocomplete="off" spellcheck="false" readonly>
                        </div>
                        <div class="field">
                            <label for="panicSite">Panic destination</label>
                            <select id="panicSite">
                                <option value="https://classroom.google.com">Google Classroom</option>
                                <option value="https://www.google.com">Google</option>
                                <option value="https://www.wikipedia.org">Wikipedia</option>
                                <option value="https://www.khanacademy.org">Khan Academy</option>
                                <option value="custom">Custom URL...</option>
                            </select>
                        </div>
                        <div class="field" id="customPanicUrl" style="display:none">
                            <label for="panicCustom">Custom panic URL</label>
                            <input type="text" id="panicCustom" placeholder="https://..." autocomplete="off" spellcheck="false">
                        </div>
                    </div>

                    <div class="panel">
                        <h3>Behavior</h3>
                        <div class="field">
                            <label class="switch">
                                <input type="checkbox" id="abCloak">
                                <span class="slider"></span>
                                Open cloaked as blob — Use a blob URL instead of about:blank.
                            </label>
                        </div>
                        <div class="field">
                            <label class="switch">
                                <input type="checkbox" id="warnClose">
                                <span class="slider"></span>
                                Warn before closing — Confirm before you leave the tab.
                            </label>
                        </div>
                    </div>

                    <div class="panel">
                        <h3>Advanced</h3>
                        <div class="field">
                            <label>Browse Engine</label>
                            <p class="field-note">How the browser rewrites sites. Scramjet is faster; Ultraviolet is more compatible.</p>
                            <div class="radio-group">
                                <label><input type="radio" name="browseEngine" value="scramjet" checked> Scramjet</label>
                                <label><input type="radio" name="browseEngine" value="ultraviolet"> Ultraviolet</label>
                            </div>
                        </div>
                        <div class="field">
                            <label>Transport</label>
                            <p class="field-note">How traffic reaches the proxy. Epoxy is faster; Libcurl works on stricter networks.</p>
                            <div class="radio-group">
                                <label><input type="radio" name="transport" value="epoxy" checked> Epoxy</label>
                                <label><input type="radio" name="transport" value="libcurl"> Libcurl</label>
                            </div>
                        </div>
                    </div>

                    <div class="panel">
                        <h3>Advertisements</h3>
                        <div class="field">
                            <label class="switch">
                                <input type="checkbox" id="enableAds" checked>
                                <span class="slider"></span>
                                Enable Ads — We ask that you keep this toggle enabled. They only affect the homepage, and UBG Ultra runs solely on ad revenue. This switch only affects popunders.
                            </label>
                        </div>
                    </div>

                    <div class="panel">
                        <h3>Information</h3>
                        <div class="field">
                            <strong>Credits</strong>
                            <ul class="credits-list">
                                <li>GN-Math</li>
                                <li>Game library</li>
                                <li>SoundCloud — Music</li>
                                <li>MercuryWorkshop</li>
                                <li>Scramjet</li>
                                <li>Titanium Network</li>
                                <li>Ultraviolet</li>
                            </ul>
                        </div>
                        <div class="field">
                            <strong>Third parties</strong>
                            <ul class="credits-list">
                                <li>Movies, shows & music</li>
                            </ul>
                        </div>
                        <div class="field">
                            <strong>Links</strong>
                            <div class="links-row">
                                <a href="#" class="link-btn">Terms of Service</a>
                                <a href="#" class="link-btn">Privacy Policy</a>
                                <a href="#" class="link-btn">DMCA</a>
                            </div>
                        </div>
                    </div>

                </div>
            </section>"""

if start_idx >= 0 and end_idx >= 0:
    new_file = content[:start_idx] + new_content + content[end_idx + len(end_marker):]
    with open(r'C:\Users\Om 2\Downloads\UBG-Ultra-main\UBG-Ultra-main\games\index.html', 'w', encoding='utf-8') as f:
        f.write(new_file)
    print("Replaced successfully!")
else:
    print("Markers not found")