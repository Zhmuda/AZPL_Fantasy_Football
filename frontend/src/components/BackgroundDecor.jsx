// Fixed, full-viewport decorative background: two soft colour glows plus a
// faint pitch-markings watermark (halfway line/centre circle top-right,
// penalty box/arc bottom-left) and a sparse dot scatter for texture.
// Purely presentational — sits behind all page content (z-index -1),
// ignores pointer events, and is hidden from screen readers.
export default function BackgroundDecor() {
  return (
    <svg
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        zIndex: -1,
        pointerEvents: "none",
      }}
    >
      <defs>
        <radialGradient id="bgGlowBlue" cx="12%" cy="0%" r="60%">
          <stop offset="0%" stopColor="#58a6ff" stopOpacity="0.16" />
          <stop offset="100%" stopColor="#58a6ff" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="bgGlowGreen" cx="92%" cy="100%" r="55%">
          <stop offset="0%" stopColor="#3fb950" stopOpacity="0.09" />
          <stop offset="100%" stopColor="#3fb950" stopOpacity="0" />
        </radialGradient>
      </defs>

      <rect width="1600" height="900" fill="#0d1117" />
      <rect width="1600" height="900" fill="url(#bgGlowBlue)" />
      <rect width="1600" height="900" fill="url(#bgGlowGreen)" />

      {/* Pitch-marking watermark */}
      <g stroke="#58a6ff" strokeOpacity="0.07" strokeWidth="2.5" fill="none">
        {/* halfway line + centre circle, top-right */}
        <line x1="1520" y1="-100" x2="1520" y2="900" />
        <circle cx="1520" cy="140" r="230" />

        {/* penalty box + arc, bottom-left */}
        <path d="M -20 620 L 260 620 L 260 900" />
        <path d="M -20 740 L 120 740 L 120 900" />
        <path d="M 60 900 A 140 140 0 0 1 260 780" />
      </g>
      <circle cx="1520" cy="140" r="4" fill="#58a6ff" fillOpacity="0.16" />

      {/* Sparse stadium-light sparkle */}
      <g fill="#e6edf3">
        <circle cx="1023.1" cy="22.5" r="1.4" fillOpacity="0.031" />
        <circle cx="1178.4" cy="609.0" r="2.2" fillOpacity="0.024" />
        <circle cx="675.1" cy="26.8" r="1.3" fillOpacity="0.045" />
        <circle cx="42.5" cy="179.0" r="1.9" fillOpacity="0.047" />
        <circle cx="352.7" cy="530.3" r="2.1" fillOpacity="0.02" />
        <circle cx="1289.3" cy="628.3" r="1.5" fillOpacity="0.028" />
        <circle cx="1531.5" cy="302.9" r="1.1" fillOpacity="0.025" />
        <circle cx="1356.0" cy="543.4" r="2.1" fillOpacity="0.056" />
        <circle cx="858.0" cy="875.8" r="1.5" fillOpacity="0.048" />
        <circle cx="1327.0" cy="556.7" r="2.2" fillOpacity="0.049" />
        <circle cx="1127.3" cy="41.2" r="1.3" fillOpacity="0.034" />
        <circle cx="127.7" cy="209.5" r="1.1" fillOpacity="0.034" />
        <circle cx="1017.1" cy="328.3" r="1.5" fillOpacity="0.03" />
        <circle cx="427.2" cy="843.0" r="1.9" fillOpacity="0.05" />
        <circle cx="273.8" cy="656.2" r="1.2" fillOpacity="0.039" />
        <circle cx="1583.2" cy="576.0" r="1.8" fillOpacity="0.054" />
        <circle cx="1348.6" cy="698.4" r="1.3" fillOpacity="0.022" />
        <circle cx="504.7" cy="241.0" r="1.3" fillOpacity="0.067" />
        <circle cx="1402.2" cy="283.2" r="1.9" fillOpacity="0.04" />
        <circle cx="1463.3" cy="413.0" r="1.4" fillOpacity="0.032" />
        <circle cx="898.2" cy="236.5" r="1.8" fillOpacity="0.065" />
        <circle cx="639.0" cy="197.4" r="2.4" fillOpacity="0.045" />
        <circle cx="145.5" cy="42.4" r="1.2" fillOpacity="0.051" />
        <circle cx="1267.3" cy="379.9" r="1.1" fillOpacity="0.039" />
        <circle cx="1593.8" cy="476.2" r="2.4" fillOpacity="0.063" />
        <circle cx="18.4" cy="648.6" r="2.0" fillOpacity="0.047" />
        <circle cx="426.9" cy="576.9" r="1.2" fillOpacity="0.042" />
        <circle cx="726.0" cy="858.4" r="2.2" fillOpacity="0.033" />
        <circle cx="800.9" cy="160.8" r="2.3" fillOpacity="0.064" />
        <circle cx="477.5" cy="575.1" r="1.9" fillOpacity="0.028" />
        <circle cx="1220.0" cy="485.4" r="2.1" fillOpacity="0.047" />
        <circle cx="0.9" cy="291.7" r="1.0" fillOpacity="0.066" />
        <circle cx="1406.0" cy="748.5" r="1.4" fillOpacity="0.023" />
        <circle cx="1404.8" cy="852.3" r="1.1" fillOpacity="0.044" />
        <circle cx="110.7" cy="684.5" r="2.1" fillOpacity="0.026" />
        <circle cx="760.5" cy="494.8" r="1.4" fillOpacity="0.064" />
        <circle cx="677.0" cy="190.6" r="1.8" fillOpacity="0.056" />
        <circle cx="321.8" cy="280.5" r="2.4" fillOpacity="0.052" />
        <circle cx="701.0" cy="465.8" r="1.2" fillOpacity="0.031" />
        <circle cx="540.9" cy="529.5" r="1.3" fillOpacity="0.031" />
        <circle cx="113.6" cy="568.0" r="1.3" fillOpacity="0.065" />
        <circle cx="1375.4" cy="63.8" r="1.3" fillOpacity="0.053" />
        <circle cx="342.8" cy="119.1" r="2.3" fillOpacity="0.049" />
        <circle cx="756.3" cy="706.2" r="2.1" fillOpacity="0.03" />
        <circle cx="155.1" cy="387.9" r="1.6" fillOpacity="0.043" />
        <circle cx="1166.5" cy="606.0" r="2.4" fillOpacity="0.025" />
        <circle cx="644.2" cy="305.4" r="2.2" fillOpacity="0.032" />
        <circle cx="304.3" cy="403.8" r="1.6" fillOpacity="0.034" />
        <circle cx="399.7" cy="830.9" r="1.6" fillOpacity="0.063" />
        <circle cx="880.5" cy="45.5" r="2.4" fillOpacity="0.062" />
        <circle cx="1550.4" cy="833.7" r="2.2" fillOpacity="0.028" />
        <circle cx="777.0" cy="192.4" r="1.6" fillOpacity="0.023" />
        <circle cx="606.4" cy="886.8" r="1.4" fillOpacity="0.059" />
        <circle cx="728.0" cy="380.7" r="2.3" fillOpacity="0.07" />
        <circle cx="889.2" cy="646.6" r="1.2" fillOpacity="0.035" />
      </g>
    </svg>
  );
}
