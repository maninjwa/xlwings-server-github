// TODO: provide your URL
const base_url = "URL";
const token = ScriptApp.getOAuthToken();

function getGithubIssues() {
  runPython(base_url + "/github/issues", { apiKey: token });
}

function onOpen() {
  // This will provide a Custom Menu
  // https://developers.google.com/apps-script/guides/menus
  let ui = SpreadsheetApp.getUi();
  ui.createMenu("GitHub")
    .addItem("Update Dashboard", "getGithubIssues")
    .addToUi();
}
