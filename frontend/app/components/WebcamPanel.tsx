"use client";
import { useEffect, useRef, useState } from "react";

export default function WebcamPanel() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("برای شروع، اجازه دسترسی به وبکم را صادر کنید.");
  const [error, setError] = useState("");

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
      setMessage("تصویر وبکم دریافت می‌شود؛ پردازش تشخیص چهره هنوز به موتور AI متصل نشده است.");
      await refreshDevices();
    } catch (e) {
      setError(e instanceof Error ? e.message : "دسترسی به وبکم ممکن نشد.");
      setMessage("وبکم فعال نشد.");
    }
  }

  useEffect(() => {
    refreshDevices().catch(() => setError("مرورگر نتوانست فهرست دوربین‌ها را بخواند."));
    return () => streamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  return (
    <section className="panel" dir="rtl">
      <div className="panel-head">
        <div><h3>وبکم لپ‌تاپ</h3><p>پیش‌نمایش زنده دوربین برای ورودی سامانه</p></div>
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
        {!running
          ? <button className="primary" onClick={startCamera}>روشن کردن وبکم</button>
          : <button className="reject" onClick={stopCamera}>خاموش کردن وبکم</button>}
      </div>
      <p style={{ color: error ? "#fb7185" : "#91a3bd", fontSize: 12, marginTop: 12 }}>{error || message}</p>
      <div className="privacy-note">حریم خصوصی: تصویر فعلاً فقط در مرورگر نمایش داده می‌شود؛ ذخیره یا به سرور ارسال نمی‌شود. تشخیص هویت و ثبت خودکار تردد تا اتصال و ارزیابی موتور AI غیرفعال است.</div>
    </section>
  );
}
