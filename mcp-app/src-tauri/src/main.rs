// src-tauri/src/main.rs
#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader, Write},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    env
};

use serde_json::json;
use tauri::{Emitter, State};

/// Allow cloning PyEngine by cloning its Arc fields.
#[derive(Clone)]
struct PyEngine {
    _child: Arc<Mutex<Child>>,
    stdin: Arc<Mutex<std::process::ChildStdin>>,
    stdout: Arc<Mutex<BufReader<std::process::ChildStdout>>>,
}

/// Tauri command — sends a query to Python.
/// IMPORTANT: This only WRITES. It does not READ (to avoid deadlocks).
/// The background thread handles reading and emitting events.
#[tauri::command]
fn send_to_python(state: State<PyEngine>, query: String) -> Result<(), String> {
    let payload = json!({ "query": query }).to_string() + "\n";

    {
        let mut stdin = state
            .stdin
            .lock()
            .map_err(|e| format!("stdin lock error: {}", e))?;
        stdin
            .write_all(payload.as_bytes())
            .map_err(|e| format!("stdin write error: {}", e))?;
        stdin.flush().map_err(|e| format!("stdin flush error: {}", e))?;
    }

    Ok(())
}

/// Launches python bridge.py and returns engine.
fn spawn_python_bridge(python_exec: &str, bridge_path: &str) -> Result<PyEngine, String> {
    let mut child = Command::new(python_exec)
        .arg("-u")
        .arg(bridge_path)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit()) // Show python errors in Tauri console
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

/// Read Python's initial handshake line
fn read_ready_line(engine: &PyEngine) -> Result<String, String> {
    let mut line = String::new();
    let mut stdout = engine
        .stdout
        .lock()
        .map_err(|e| format!("stdout lock error: {}", e))?;
    stdout
        .read_line(&mut line)
        .map_err(|e| format!("read_line error: {}", e))?;
    Ok(line)
}

fn main() {
    let python_executable = "python";
    // Ensure this path is correct on your machine
    let mut bridge_path = env::current_dir().expect("Failed to get current working directory");
    bridge_path.push(".."); // Up to mcp-app
    bridge_path.push(".."); // Up to mcp-project
    bridge_path.push("client");
    bridge_path.push("bridge.py");
    println!("[RUST] Looking for bridge at: {:?}", bridge_path);

    if !bridge_path.exists() {
        eprintln!("CRITICAL ERROR: Could not find bridge.py!");
        eprintln!("Expected location: {:?}", bridge_path);
        // Don't crash immediately, let the spawn function fail so you see the error
    }
    let bridge_path_str = bridge_path.to_str().expect("Path is not valid UTF-8");
    // Start python
    let engine = spawn_python_bridge(python_executable, bridge_path_str)
        .expect("Could not start python bridge");

    // Perform handshake
    match read_ready_line(&engine) {
        Ok(line) => println!("Python bridge handshake: {}", line.trim()),
        Err(e) => eprintln!("Handshake failed: {}", e),
    }

    let engine_state = engine.clone();

    tauri::Builder::default()
        .manage(engine_state.clone())
        .setup(move |app| {
            // Clone the app handle so it can be moved to the thread safely
            let app_handle = app.handle().clone();
            let engine_for_thread = engine_state.clone();

            // Stream python output continuously in the background
            thread::spawn(move || {
                let mut stdout = engine_for_thread.stdout.lock().unwrap();

                // Iterate over a mutable borrow `(&mut *stdout)`
                // This prevents moving the internal BufReader out of the MutexGuard
                for line in (&mut *stdout).lines() {
                    if let Ok(text) = line {
                        println!("[PYTHON STREAM] {}", text);

                        // Emit event to frontend React
                        let _ = app_handle.emit("python-output", text);
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![send_to_python])
        .run(tauri::generate_context!())
        .expect("error while running Tauri");
}