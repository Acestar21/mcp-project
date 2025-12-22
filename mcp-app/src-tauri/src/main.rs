#![cfg_attr(all(not(debug_assertions), target_os = "windows"), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader, Write},
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
};

use tauri::{Emitter, Manager, State};

#[derive(Clone)]
struct PyEngine {
    _child: Arc<Mutex<Child>>,
    stdin: Arc<Mutex<std::process::ChildStdin>>,
    stdout: Arc<Mutex<BufReader<std::process::ChildStdout>>>,
}

/* ---------------- Python command selection ---------------- */

fn python_command(app: &tauri::AppHandle) -> (String, Vec<String>) {
    if cfg!(debug_assertions) {
        // DEV → run python bridge.py
        let mut path = std::env::current_dir().unwrap();
        path.push("..");
        path.push("..");
        path.push("client");
        path.push("bridge.py");

        (
            "python".to_string(),
            vec!["-u".into(), path.to_string_lossy().into()],
        )
    } else {
        // PROD → run bundled python-agent.exe
        let resource_dir = app
            .path()
            .resource_dir()
            .expect("resource_dir not found");

        let exe = resource_dir.join("python").join("python-agent.exe");
        println!("[RUST] Using python agent at: {:?}", exe);

        (exe.to_string_lossy().into(), vec![])
    }
}

/* ---------------- Spawn Python ---------------- */

fn spawn_python_bridge(app: &tauri::AppHandle) -> Result<PyEngine, String> {
    let (command, args) = python_command(app);

    let mut child = Command::new(command)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| e.to_string())?;

    let stdin = child.stdin.take().ok_or("stdin missing")?;
    let stdout = child.stdout.take().ok_or("stdout missing")?;

    Ok(PyEngine {
        _child: Arc::new(Mutex::new(child)),
        stdin: Arc::new(Mutex::new(stdin)),
        stdout: Arc::new(Mutex::new(BufReader::new(stdout))),
    })
}

/* ---------------- READY handshake ---------------- */

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

/* ---------------- IPC write-only ---------------- */

fn send_raw_json(engine: &PyEngine, json: &str) -> Result<(), String> {
    let mut stdin = engine.stdin.lock().unwrap();
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

#[tauri::command]
fn get_config_dir(app: tauri::AppHandle) -> String {
    app.path()
        .app_config_dir()
        .unwrap()
        .to_string_lossy()
        .to_string()
}

/* ---------------- App entry ---------------- */

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let engine = spawn_python_bridge(&app.handle())
                .expect("Failed to start python bridge");

            // READY gate
            wait_for_ready(&engine)
                .expect("Python bridge did not send READY");

            let app_handle = app.handle().clone();
            let engine_clone = engine.clone();

            // Store engine in Tauri state
            app.manage(engine);

            // Background reader thread
            thread::spawn(move || {
                let mut stdout = engine_clone.stdout.lock().unwrap();

                for line in (&mut *stdout).lines() {
                    if let Ok(text) = line {
                        println!("[PYTHON STREAM] {}", text);

                        if let Ok(value) = serde_json::from_str::<serde_json::Value>(&text) {
                            if let Some(event_type) =
                                value.get("type").and_then(|v| v.as_str())
                            {
                                match event_type {
                                    "capabilities" => {
                                        let _ = app_handle.emit("capabilities", value);
                                    }
                                    _ => {
                                        let _ = app_handle.emit("agent_event", value);
                                    }
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
