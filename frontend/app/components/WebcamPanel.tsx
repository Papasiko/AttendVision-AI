"use client";
import { useEffect, useRef, useState } from "react";

type Employee = { id: number; full_name: string; employee_code: string; status: string; face_enrolled?: boolean };
type Props = { token: string; employees: Employee[]; onComplete: () => void };
type Result = { matched: boolean; employee_id?: number | null; employee_name?: string | null; score: number; event_id?: number | null; message: string };

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function WebcamPanel({ token, employees, onComplete }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [running, setRunning] = useState(false);
  const [employeeId, setEmployeeId] = useState("");
  const [consent, setConsent] = useState(false);
  const [direction, setDirection] = useState<"in" | "out">("in");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("برای شروع، اجازه دسترسی به وبکم را صادر کنید.");
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  async function refreshDevices() {
    const all = await navigator.mediaDevices.enumerateDevices();
    const cameras = all.filter((item) => item.kind === "videoinput");
    setDevices(cameras);
    if (!deviceId && cameras[0]) setDeviceId(cameras[0].deviceId);
  }

  function stopCamera() {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setRunning(false);
    setMessage("وبکم خاموش است.");
  }

  async function startCamera() {
    setError("");
    try {
      stopCamera();
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: deviceId ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } } : { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setRunning(true);
      setMessage("وبکم آماده است. برای هر عملیات، عکس فقط با فشردن دکمه ارسال می‌شود.");
      await refreshDevices();
    } catch (e) {
      setError(e instanceof Error ? e.message : "دسترسی به وبکم ممکن نشد.");
      setMessage("وبکم فعال نشد.");
    }
  }

  async function capture(): Promise<Blob> {
    const video = videoRef.current;
    if (!video || !video.videoWidth) throw new Error("ابتدا وبکم را روشن کنید.");
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("امکان پردازش تصویر وجود ندارد.");
    context.drawImage(video, 0, 0);
    return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("گرفتن تصویر ناموفق بود.")), "image/jpeg", 0.9));
  }


  async function deleteTemplate() {
    if (!employeeId || !window.confirm("Delete this employee's stored face template?")) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(API + "/api/v1/employees/" + employeeId + "/face-template", { method: "DELETE", headers: { Authorization: "Bearer " + token } });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Template deletion failed.");
      setMessage("Stored face template deleted.");
      onComplete();
    } catch (e) { setError(e instanceof Error ? e.message : "Template deletion failed."); }
    finally { setBusy(false); }
  }

  async function send(path: string, fields: Record<string, string>) {
    setBusy(true); setError(""); setResult(null);
    try {
      const blob = await capture();
      const form = new FormData();
      for (const [key, value] of Object.entries(fields)) form.append(key, value);
      form.append("image", blob, "webcam.jpg");
      const response = await fetch(API + path, { method: "POST", headers: { Authorization: "Bearer " + token }, body: form });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "خطای " + response.status);
      if (path === "/api/v1/face/recognize") {
        setResult(body as Result);
        setMessage("رویداد در صف بازبینی ثبت شد؛ هنوز حضور قطعی محسوب نمی‌شود.");
        onComplete();
      } else {
        setMessage(body.message || "قالب چهره ثبت شد.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "عملیات ناموفق بود.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    refreshDevices().catch(() => setError("مرورگر نتوانست فهرست دوربین‌ها را بخواند."));
    return () => streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  return (
    <section className="panel" dir="rtl">
      <div className="panel-head">
        <div><h3>وبکم و تشخیص چهره</h3><p>پردازش محلی مدل؛ ارسال عکس فقط با اقدام صریح اپراتور</p></div>
        <span className={running ? "pill green" : "pill amber"}>{running ? "دوربین روشن" : "دوربین خاموش"}</span>
      </div>
      <div style={{ background: "#050a13", borderRadius: 12, overflow: "hidden", aspectRatio: "16 / 9", display: "grid", placeItems: "center", border: "1px solid #293b55" }}>
        <video ref={videoRef} autoPlay muted playsInline style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        {!running && <span style={{ color: "#8293aa" }}>پیش‌نمایش وبکم</span>}
      </div>
      <div className="inline-form" style={{ marginTop: 14 }}>
        <select aria-label="انتخاب وبکم" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} disabled={running}>
          {devices.length === 0 && <option value="">وبکمی پیدا نشد</option>}
          {devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `دوربین ${index + 1}`}</option>)}
        </select>
        {!running ? <button className="primary" onClick={startCamera}>روشن کردن وبکم</button> : <button className="reject" onClick={stopCamera}>خاموش کردن وبکم</button>}
      </div>
      <div style={{ borderTop: "1px solid #26364e", marginTop: 20, paddingTop: 16 }}>
        <h3>ثبت‌نام چهره کارمند</h3>
        <p style={{ color: "#91a3bd", fontSize: 11 }}>فقط با رضایت صریح و ثبت‌شده کارمند. قالب استخراج‌شده رمزنگاری می‌شود و عکس خام ذخیره نمی‌شود.</p>
        <div className="inline-form">
          <select value={employeeId} onChange={e => setEmployeeId(e.target.value)}>
            <option value="">انتخاب کارمند</option>
            {employees.filter(e => e.status === "active").map(e => <option key={e.id} value={e.id}>{e.employee_code} — {e.full_name}{e.face_enrolled ? " (enrolled)" : ""}</option>)}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 8, color: "#c5d2e3", fontSize: 11 }}>
            <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
            رضایت صریح کارمند دریافت شده است
          </label>
          <button className="primary" disabled={!running || !employeeId || !consent || busy} onClick={() => send(`/api/v1/employees/${employeeId}/face-enroll`, { consent: "true" })}>Enroll Face Template</button>
          <button className="reject" disabled={!employeeId || !employees.some(e => String(e.id) === employeeId && e.face_enrolled) || busy} onClick={deleteTemplate}>Delete Stored Template</button>
        </div>
      </div>
      <div style={{ borderTop: "1px solid #26364e", marginTop: 20, paddingTop: 16 }}>
        <h3>ثبت نامزد ورود / خروج</h3>
        <div className="inline-form">
          <select value={direction} onChange={e => setDirection(e.target.value as "in" | "out")}>
            <option value="in">ورود</option><option value="out">خروج</option>
          </select>
          <button className="primary" disabled={!running || busy} onClick={() => send("/api/v1/face/recognize", { direction })}>{busy ? "در حال پردازش..." : "شناسایی و ثبت برای بازبینی"}</button>
        </div>
      </div>
      {result && <div className="privacy-note">{result.message}{result.employee_name ? ` نامزد: ${result.employee_name}.` : ""} امتیاز شباهت: {result.score.toFixed(3)} · شناسه رویداد: {result.event_id}</div>}
      <p style={{ color: error ? "#fb7185" : "#91a3bd", fontSize: 12, marginTop: 12 }}>{error || message}</p>
      <div className="privacy-note">هشدار: تطبیق چهره ممکن است اشتباه کند و امتیاز خام احتمال صحت نیست. همه نتایج فقط pending هستند و مدیر باید هویت و تردد را بررسی کند. این سیستم liveness ندارد و در برابر عکس/ویدئو یا جعل هویت مقاوم‌سازی نشده؛ برای تصمیم انضباطی یا کنترل دسترسی استفاده نشود.</div>
    </section>
  );
}
