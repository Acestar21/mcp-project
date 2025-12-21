// src-tauri/src/main.rs
#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader, Write},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    env
};

use tauri::{Emitter, State};

#[derive(Clone)]
struct PyEngine {
    _child: Arc<Mutex<Child>>,
    stdin: Arc<Mutex<std::process::ChildStdin>>,
    stdout: Arc<Mutex<BufReader<std::process::ChildStdout>>>,
}

/// Read exactly one READY line from Python
fn wait_for_ready(engine: &PyEngine) -> Result<(), String> {
    let mut line = String::new();
    let mut stdout = engine.stdout.lock().unwrap();

    stdout.read_line(&mut line).map_err(|e| e.to_string())?;

    if line.trim() != "READY" {
        return Err(format!("Expected READY, got: {}", line));
    }

    println!("[RUST] Python bridge READY");
    Ok(())
}

/// Send raw JSON to Python (write-only)
fn send_raw_json(state: &PyEngine, json: &str) -> Result<(), String> {
    let mut stdin = state.stdin.lock().unwrap();
    stdin.write_all(json.as_bytes()).map_err(|e| e.to_string())?;
    stdin.write_all(b"\n").map_err(|e| e.to_string())?;
    stdin.flush().map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
fn send_to_python(state: State<PyEngine>, query: String) -> Result<(), String> {
    let payload = format!(r#"{{"query":"{}"}}"#, query);
    send_raw_json(&state, &payload)
}

fn spawn_python_bridge(python_exec: &str, bridge_path: &str) -> Result<PyEngine, String> {
    let mut child = Command::new(python_exec)
        .arg("-u")
        .arg(bridge_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| format!("Failed to spawn python bridge: {}", e))?;

    let child_stdin = child.stdin.take().ok_or("Failed to open child stdin")?;
    let child_stdout = child.stdout.take().ok_or("Failed to open child stdout")?;

    Ok(PyEngine {
        _child: Arc::new(Mutex::new(child)),
        stdin: Arc::new(Mutex::new(child_stdin)),
        stdout: Arc::new(Mutex::new(BufReader::new(child_stdout))),
    })
}

fn main() {
    let python_executable = "python";

    let mut bridge_path = env::current_dir().unwrap();
    bridge_path.push("..");
    bridge_path.push("..");
    bridge_path.push("client");
    bridge_path.push("bridge.py");

    println!("[RUST] Looking for bridge at: {:?}", bridge_path);

    let engine = spawn_python_bridge(python_executable, bridge_path.to_str().unwrap())
        .expect("Could not start python bridge");

    // 🔑 READY gate (nothing JSON is consumed here)
    wait_for_ready(&engine).expect("Python bridge did not send READY");

    let engine_state = engine.clone();

    tauri::Builder::default()
        .manage(engine_state.clone())
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let engine_for_thread = engine_state.clone();

            thread::spawn(move || {
                let mut stdout = engine_for_thread.stdout.lock().unwrap();

                for line in (&mut *stdout).lines() {
                    if let Ok(text) = line {
                        println!("[PYTHON STREAM] {}", text);

                        if let Ok(value) = serde_json::from_str::<serde_json::Value>(&text) {
                            match value.get("type").and_then(|t| t.as_str()) {
                                Some("capabilities") => {
                                    let _ = app_handle.emit("capabilities", value);
                                }
                                _ => {
                                    let _ = app_handle.emit("agent_event", value);
                                }
                            }
                        }
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![send_to_python])
        .run(tauri::generate_context!())
        .expect("error while running Tauri");
}
