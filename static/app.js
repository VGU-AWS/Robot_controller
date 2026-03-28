const output = document.getElementById("output");
const pages = {
  landing: document.getElementById("page-landing"),
  robots: document.getElementById("page-robots"),
  commands: document.getElementById("page-commands"),
};

const registerNameInput = document.getElementById("registerName");
const userInfo = document.getElementById("userInfo");
const connectedRobotInfo = document.getElementById("connectedRobotInfo");
const availableCount = document.getElementById("availableCount");
const commandButtonsWrap = document.getElementById("commandButtons");

const commandMap = [
  { key: "F", label: "Forward" },
  { key: "B", label: "Backward" },
  { key: "L", label: "Left" },
  { key: "R", label: "Right" },
  { key: "S", label: "Stop" },
  { key: "I", label: "Forward Right" },
  { key: "J", label: "Backward Right" },
  { key: "G", label: "Forward Left" },
  { key: "H", label: "Backward Left" },
];

const state = {
  baseUrl: window.location.origin,
  userToken: null,
  userName: null,
  robotId: null,
  robotName: null,
};

function setCookie(name, value, days = 7) {
  const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getCookie(name) {
  const key = `${name}=`;
  const parts = document.cookie.split(";").map((part) => part.trim());
  for (const part of parts) {
    if (part.startsWith(key)) {
      return decodeURIComponent(part.slice(key.length));
    }
  }
  return null;
}

function clearCookie(name) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=Lax`;
}

function writeOutput(title, payload) {
  output.textContent = `${title}\n\n${JSON.stringify(payload, null, 2)}`;
}

async function request(path, options = {}) {
  const response = await fetch(`${state.baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data;
  try {
    data = await response.json();
  } catch {
    data = { detail: "Non-JSON response" };
  }

  if (!response.ok) {
    throw { status: response.status, data };
  }

  return data;
}

function showPage(pageName) {
  Object.entries(pages).forEach(([name, page]) => {
    page.classList.toggle("hidden", name !== pageName);
  });
}

function syncUIState() {
  userInfo.textContent = state.userName ? `${state.userName}` : "-";
  connectedRobotInfo.textContent = state.robotId
    ? `${state.robotName || "Robot"} (#${state.robotId})`
    : "None";

  const loggedIn = Boolean(state.userToken);
  document.getElementById("logoutBtn").disabled = !loggedIn;

  if (!loggedIn) {
    showPage("landing");
    return;
  }

  if (state.robotId) {
    showPage("commands");
  } else {
    showPage("robots");
  }
}

function saveSessionCookies() {
  if (state.userToken) {
    setCookie("user_token", state.userToken);
  }
  if (state.userName) {
    setCookie("user_name", state.userName);
  }
  if (state.robotId) {
    setCookie("robot_id", String(state.robotId));
  }
  if (state.robotName) {
    setCookie("robot_name", state.robotName);
  }
}

function clearSession() {
  state.userToken = null;
  state.userName = null;
  state.robotId = null;
  state.robotName = null;

  clearCookie("user_token");
  clearCookie("user_name");
  clearCookie("robot_id");
  clearCookie("robot_name");

  syncUIState();
}

async function refreshAvailableRobots() {
  try {
    const data = await request("/robots/available");
    availableCount.textContent = String(data.available_robots);
    writeOutput("Available robots refreshed", data);
  } catch (error) {
    writeOutput("Refresh available robots failed", error);
  }
}

async function registerUser() {
  const name = registerNameInput.value.trim();
  if (!name) {
    writeOutput("Register user failed", { detail: "Name is required" });
    return;
  }

  try {
    const data = await request("/register/user", {
      method: "POST",
      body: JSON.stringify({ name }),
    });

    state.userName = data.name;
    state.userToken = data.user_token;
    state.robotId = null;
    state.robotName = null;
    saveSessionCookies();

    syncUIState();
    writeOutput("User registered", data);
    await refreshAvailableRobots();
  } catch (error) {
    writeOutput("Register user failed", error);
  }
}

async function connectFreeRobot() {
  if (!state.userToken) {
    writeOutput("Connect failed", { detail: "Please register/login first" });
    return;
  }

  try {
    const data = await request("/user/assign-free-robot", {
      method: "POST",
      headers: { "X-User-Token": state.userToken },
    });

    state.robotId = data.robot_id;
    state.robotName = data.robot_name;
    saveSessionCookies();

    syncUIState();
    writeOutput("Robot connected", data);
    await refreshAvailableRobots();
  } catch (error) {
    writeOutput("Connect robot failed", error);
  }
}

async function sendCommand(commandKey) {
  if (!state.userToken || !state.robotId) {
    writeOutput("Send command failed", { detail: "Connect a robot first" });
    return;
  }

  try {
    const data = await request("/user/send-command", {
      method: "POST",
      headers: { "X-User-Token": state.userToken },
      body: JSON.stringify({ robot_id: state.robotId, command_text: commandKey }),
    });
    writeOutput(`Command ${commandKey} sent`, data);
  } catch (error) {
    writeOutput(`Command ${commandKey} failed`, error);
  }
}

async function releaseRobot() {
  if (!state.userToken) {
    writeOutput("Release failed", { detail: "Please login first" });
    return;
  }

  try {
    const data = await request("/user/release-current-robot", {
      method: "POST",
      headers: { "X-User-Token": state.userToken },
    });

    state.robotId = null;
    state.robotName = null;
    clearCookie("robot_id");
    clearCookie("robot_name");

    syncUIState();
    writeOutput("Robot freed", data);
    await refreshAvailableRobots();
  } catch (error) {
    writeOutput("Release robot failed", error);
  }
}

function renderCommandButtons() {
  commandButtonsWrap.innerHTML = "";
  commandMap.forEach((cmd) => {
    const button = document.createElement("button");
    button.className = "command-btn";
    button.textContent = `${cmd.key} (${cmd.label})`;
    button.addEventListener("click", () => sendCommand(cmd.key));
    commandButtonsWrap.appendChild(button);
  });
}

function loadSessionFromCookies() {
  state.userToken = getCookie("user_token");
  state.userName = getCookie("user_name");
  const robotIdCookie = getCookie("robot_id");
  state.robotId = robotIdCookie ? Number(robotIdCookie) : null;
  state.robotName = getCookie("robot_name");

  if (!state.userToken) {
    clearSession();
    return;
  }

  syncUIState();
}

document.getElementById("registerBtn").addEventListener("click", registerUser);
document.getElementById("refreshRobotsBtn").addEventListener("click", refreshAvailableRobots);
document.getElementById("connectRobotBtn").addEventListener("click", connectFreeRobot);
document.getElementById("releaseRobotBtn").addEventListener("click", releaseRobot);
document.getElementById("logoutBtn").addEventListener("click", () => {
  clearSession();
  writeOutput("Logged out", { message: "Session cleared from cookies" });
});

renderCommandButtons();
loadSessionFromCookies();
refreshAvailableRobots();
