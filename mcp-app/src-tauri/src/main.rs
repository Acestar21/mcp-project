// src-tauri/src/main.rs
#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use std::process::{Command, Stdio, Child};
use std::io::{Write, BufRead, BufReader};
use std::sync::{Arc, Mutex};
use tauri::{Manager, State};
use serde_json::json;

struct PyEngine {
    child: Arc<Mutex<Child>>,
    stdin: Arc<Mutex<std::process::ChildStdin>>,
    stdout: Arc<Mutex<BufReader<std::process::ChildStdout>>>,
}

#[tauri::command]
fn send_to_python(state: State<PyEngine>, query: String) -> Result<String, String> {
  // send JSON line to python, wait for single-line JSON response
    let payload = json!({ "query": query }).to_string() + "\n";

  // write
    {
    let mut stdin = state.stdin.lock().map_err(|e| format!("stdin lock error: {}", e))?;
    stdin.write_all(payload.as_bytes()).map_err(|e| format!("stdin write error: {}", e))?;
    stdin.flush().map_err(|e| format!("stdin flush error: {}", e))?;
    }

  // read one line
    let mut line = String::new();
    {
    let mut stdout = state.stdout.lock().map_err(|e| format!("stdout lock error: {}", e))?;
    stdout.read_line(&mut line).map_err(|e| format!("stdout read error: {}", e))?;
    }

    Ok(line)
}

fn spawn_python_bridge(python_exec: &str, bridge_path: &str) -> Result<PyEngine, String> {
    let mut child = Command::new(python_exec)
    .arg("-u") // unbuffered
    .arg(bridge_path)
    .stdin(Stdio::piped())
    .stdout(Stdio::piped())
    .stderr(Stdio::inherit()) // let stderr go to tauri console for debugging
    .spawn()
    .map_err(|e| format!("Failed to spawn python bridge: {}", e))?;

  // Take pipes
    let child_stdin = child.stdin.take().ok_or("Failed to open child stdin")?;
    let child_stdout = child.stdout.take().ok_or("Failed to open child stdout")?;
    let buf = BufReader::new(child_stdout);

    let engine = PyEngine {
    child: Arc::new(Mutex::new(child)),
    stdin: Arc::new(Mutex::new(child_stdin)),
    stdout: Arc::new(Mutex::new(buf)),
    };

    Ok(engine)
}

fn read_ready_line(engine: &PyEngine) -> Result<String, String> {
    let mut line = String::new();
    let mut stdout = engine.stdout.lock().map_err(|e| format!("stdout lock error: {}", e))?;
    stdout.read_line(&mut line).map_err(|e| format!("read_line error: {}", e))?;
    Ok(line)
}

fn main() {
  // Adjust these paths if your project layout is different.
  let python_executable = "python"; // or full path e.g. "C:\\Python311\\python.exe"
  let bridge_rel_path = "D:\\Programming\\Projects\\mcp-project\\client\\bridge.py"; // relative to src-tauri dir when running in dev

  // spawn python bridge
    let engine = spawn_python_bridge(python_executable, bridge_rel_path)
    .expect("Could not start Python bridge. Ensure python is on PATH and bridge.py exists.");

  // read initial ready handshake
    match read_ready_line(&engine) {
    Ok(line) => {
      // Optionally parse and log; for now we print to console
        println!("Python bridge handshake: {}", line.trim_end());
    }
    Err(e) => {
        eprintln!("Failed to read handshake from python bridge: {}", e);
    }
    }

  // move engine into managed state for Tauri commands
    let engine_state = engine;

    tauri::Builder::default()
    .manage(engine_state)
    .invoke_handler(tauri::generate_handler![send_to_python])
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
