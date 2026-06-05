#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

let React = null;
let ReactDOMServer = null;
let sharp = null;
let iconSets = null;

try {
  React = require("react");
  ReactDOMServer = require("react-dom/server");
  sharp = require("sharp");
  iconSets = {
    fa: require("react-icons/fa"),
    md: require("react-icons/md"),
    hi: require("react-icons/hi"),
    bi: require("react-icons/bi"),
  };
} catch (_error) {
  iconSets = null;
}

const LAYOUT = {
  width: 13.333,
  height: 7.5,
  margin: 0.55,
};

const DEFAULT_THEME = {
  name: "Crisp Teal",
  colors: {
    primary: "0F766E",
    secondary: "155E75",
    accent: "F97316",
    background: "F8FAFC",
    surface: "FFFFFF",
    text: "0F172A",
    muted: "64748B",
    inverse: "FFFFFF",
    line: "CBD5E1",
  },
  fonts: {
    heading: "Aptos Display",
    body: "Aptos",
  },
};

const SAMPLE_SPEC = {
  title: "Agentic AI: From Acronyms to Applications",
  subtitle: "A scenario-first tour of modern AI systems",
  author: "GitHub Copilot",
  theme: DEFAULT_THEME,
  slides: [
    {
      type: "title",
      title: "Agentic AI",
      subtitle: "From Acronyms to Applications",
      eyebrow: "Scenario workshop",
      notes: "Open by setting expectations. This is about judgment, not vocabulary memorization.",
    },
    {
      type: "section",
      title: "The Big Shift",
      subtitle: "From asking for answers to designing workflows.",
    },
    {
      type: "bullets",
      title: "What Makes A System Agentic?",
      kicker: "Look for delegation, context, tools, and feedback loops.",
      items: ["A goal that persists", "Tools it can use", "Memory or context", "A way to evaluate progress"],
      icon: "FaRoute",
    },
    {
      type: "twoColumn",
      title: "Assistant vs. Agent",
      left: { heading: "Assistant", items: ["Answers one prompt", "Mostly stateless", "User drives each step"] },
      right: { heading: "Agent", items: ["Works toward an outcome", "Uses tools", "Plans, checks, and revises"] },
    },
    {
      type: "process",
      title: "A Practical Agent Loop",
      steps: [
        { title: "Plan", body: "Break the goal into steps.", icon: "FaMapSigns" },
        { title: "Act", body: "Call tools and gather evidence.", icon: "FaTools" },
        { title: "Check", body: "Validate output against the goal.", icon: "FaCheckCircle" },
        { title: "Revise", body: "Adjust the plan when reality pushes back.", icon: "FaSyncAlt" }
      ],
    },
    {
      type: "chart",
      title: "Where Autonomy Helps",
      chartType: "bar",
      labels: ["Search", "Drafting", "Coding", "Ops"],
      series: [{ name: "Fit", values: [55, 70, 82, 64] }],
    },
    {
      type: "quote",
      quote: "The skill is not asking the model for magic. The skill is building the loop around it.",
      attribution: "Workshop framing",
    },
    {
      type: "closing",
      title: "Design the workflow",
      subtitle: "Then let the model help you move through it.",
    },
  ],
};

function usage() {
  console.error("Usage:");
  console.error("  node scripts/create_pptxgenjs_deck.js spec.json output.pptx");
  console.error("  node scripts/create_pptxgenjs_deck.js --sample spec.json");
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function mergeTheme(theme = {}) {
  return {
    ...clone(DEFAULT_THEME),
    ...theme,
    colors: { ...DEFAULT_THEME.colors, ...(theme.colors || {}) },
    fonts: { ...DEFAULT_THEME.fonts, ...(theme.fonts || {}) },
  };
}

function cleanHex(value, label = "color") {
  if (typeof value !== "string") {
    throw new Error(`${label} must be a 6-character hex string without #`);
  }
  const normalized = value.trim().replace(/^#/, "").toUpperCase();
  if (!/^[0-9A-F]{6}$/.test(normalized)) {
    throw new Error(`${label} must be a 6-character hex string without # or alpha transparency: ${value}`);
  }
  return normalized;
}

function normalizeThemeColors(theme) {
  const colors = {};
  for (const [name, value] of Object.entries(theme.colors)) {
    colors[name] = cleanHex(value, `theme.colors.${name}`);
  }
  return { ...theme, colors };
}

function shapeType(pres, name) {
  const shapes = pres.ShapeType || pres.shapes || {};
  return shapes[name] || shapes[name.toUpperCase()] || name;
}

function chartType(pres, name) {
  const charts = pres.ChartType || pres.charts || {};
  const key = String(name || "bar").toLowerCase();
  const map = {
    bar: charts.bar || charts.BAR || "bar",
    line: charts.line || charts.LINE || "line",
    pie: charts.pie || charts.PIE || "pie",
    doughnut: charts.doughnut || charts.DOUGHNUT || "doughnut",
  };
  return map[key] || map.bar;
}

function shadow(opacity = 0.14, angle = 45) {
  return { type: "outer", color: "000000", opacity, blur: 2, angle, distance: 1 };
}

function addNotes(slide, notes) {
  if (notes && typeof slide.addNotes === "function") {
    slide.addNotes(Array.isArray(notes) ? notes.join("\n") : String(notes));
  }
}

function addHeader(slide, pres, theme, title, options = {}) {
  if (!title) return;
  const color = options.inverse ? theme.colors.inverse : theme.colors.text;
  slide.addText(title, {
    x: LAYOUT.margin,
    y: 0.34,
    w: LAYOUT.width - LAYOUT.margin * 2,
    h: 0.55,
    margin: 0,
    fontFace: theme.fonts.heading,
    fontSize: options.size || 28,
    bold: true,
    color,
    fit: "shrink",
  });
}

function addFooter(slide, theme, text) {
  if (!text) return;
  slide.addText(text, {
    x: LAYOUT.margin,
    y: 7.0,
    w: 7,
    h: 0.2,
    margin: 0,
    fontFace: theme.fonts.body,
    fontSize: 8,
    color: theme.colors.muted,
  });
}

function addAccentBar(slide, pres, theme, x, y, h, color = theme.colors.accent) {
  slide.addShape(shapeType(pres, "rect"), {
    x,
    y,
    w: 0.08,
    h,
    fill: { color },
    line: { color },
  });
}

function addCard(slide, pres, theme, x, y, w, h, options = {}) {
  slide.addShape(shapeType(pres, "roundRect"), {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    fill: { color: options.fill || theme.colors.surface },
    line: { color: options.line || theme.colors.line, transparency: 20 },
    shadow: shadow(0.08),
  });
}

function bulletRuns(items) {
  return (items || []).map((item, index, array) => ({
    text: String(item),
    options: { bullet: true, breakLine: index < array.length - 1 },
  }));
}

function addBullets(slide, theme, items, x, y, w, h, options = {}) {
  slide.addText(bulletRuns(items), {
    x,
    y,
    w,
    h,
    margin: 0.08,
    fontFace: theme.fonts.body,
    fontSize: options.fontSize || 18,
    color: options.color || theme.colors.text,
    fit: "shrink",
    breakLine: false,
    paraSpaceAfterPt: options.paraSpaceAfterPt || 8,
  });
}

function getIconComponent(iconName) {
  if (!iconSets || !iconName) return null;
  for (const set of Object.values(iconSets)) {
    if (set[iconName]) return set[iconName];
  }
  return null;
}

async function iconToBase64(iconName, color) {
  const Icon = getIconComponent(iconName);
  if (!Icon || !React || !ReactDOMServer || !sharp) return null;
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { color: `#${cleanHex(color)}`, size: "256" })
  );
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return `data:image/png;base64,${pngBuffer.toString("base64")}`;
}

async function addIconBubble(slide, pres, theme, iconName, x, y, size = 0.52, options = {}) {
  const fill = options.fill || theme.colors.primary;
  const iconColor = options.iconColor || theme.colors.inverse;
  slide.addShape(shapeType(pres, "ellipse"), {
    x,
    y,
    w: size,
    h: size,
    fill: { color: fill },
    line: { color: fill },
  });
  const iconData = await iconToBase64(iconName, iconColor);
  if (iconData) {
    slide.addImage({ data: iconData, x: x + size * 0.22, y: y + size * 0.22, w: size * 0.56, h: size * 0.56, altText: iconName });
  } else {
    const fallback = iconName ? iconName.replace(/^Fa|^Md|^Hi|^Bi/, "").slice(0, 1) : "";
    slide.addText(fallback, {
      x,
      y: y + size * 0.13,
      w: size,
      h: size * 0.5,
      margin: 0,
      align: "center",
      fontFace: theme.fonts.heading,
      fontSize: 14,
      bold: true,
      color: iconColor,
    });
  }
}

function defineMasters(pres, theme) {
  pres.defineSlideMaster({ title: "TITLE_DARK", background: { color: theme.colors.primary }, objects: [] });
  pres.defineSlideMaster({ title: "SECTION_DARK", background: { color: theme.colors.secondary }, objects: [] });
  pres.defineSlideMaster({ title: "CONTENT", background: { color: theme.colors.background }, objects: [] });
  pres.defineSlideMaster({ title: "BLANK", background: { color: theme.colors.surface }, objects: [] });
}

async function buildTitleSlide(pres, theme, spec) {
  const slide = pres.addSlide({ masterName: "TITLE_DARK" });
  slide.background = { color: theme.colors.primary };
  slide.addShape(shapeType(pres, "rect"), { x: 0, y: 6.58, w: LAYOUT.width, h: 0.92, fill: { color: theme.colors.accent }, line: { color: theme.colors.accent } });
  if (spec.eyebrow) {
    slide.addText(String(spec.eyebrow).toUpperCase(), {
      x: 0.78,
      y: 0.82,
      w: 7,
      h: 0.28,
      margin: 0,
      fontFace: theme.fonts.body,
      fontSize: 12,
      bold: true,
      color: theme.colors.inverse,
      charSpacing: 1.8,
    });
  }
  slide.addText(spec.title || "Untitled Deck", {
    x: 0.78,
    y: 1.58,
    w: 8.8,
    h: 1.55,
    margin: 0,
    fontFace: theme.fonts.heading,
    fontSize: 46,
    bold: true,
    color: theme.colors.inverse,
    fit: "shrink",
  });
  if (spec.subtitle) {
    slide.addText(spec.subtitle, {
      x: 0.82,
      y: 3.42,
      w: 7.8,
      h: 0.72,
      margin: 0,
      fontFace: theme.fonts.body,
      fontSize: 21,
      color: theme.colors.inverse,
      transparency: 8,
      fit: "shrink",
    });
  }
  await addIconBubble(slide, pres, theme, spec.icon || "FaCompass", 10.75, 1.35, 1.2, { fill: theme.colors.accent });
  addNotes(slide, spec.notes);
}

async function buildSectionSlide(pres, theme, spec) {
  const slide = pres.addSlide({ masterName: "SECTION_DARK" });
  slide.background = { color: theme.colors.secondary };
  slide.addShape(shapeType(pres, "rect"), { x: 0, y: 0, w: 0.36, h: LAYOUT.height, fill: { color: theme.colors.accent }, line: { color: theme.colors.accent } });
  slide.addText(spec.title || "Section", {
    x: 0.9,
    y: 2.34,
    w: 9.8,
    h: 0.85,
    margin: 0,
    fontFace: theme.fonts.heading,
    fontSize: 42,
    bold: true,
    color: theme.colors.inverse,
    fit: "shrink",
  });
  if (spec.subtitle) {
    slide.addText(spec.subtitle, {
      x: 0.92,
      y: 3.42,
      w: 8.2,
      h: 0.55,
      margin: 0,
      fontFace: theme.fonts.body,
      fontSize: 18,
      color: theme.colors.inverse,
      transparency: 10,
    });
  }
  addNotes(slide, spec.notes);
}

async function buildBulletsSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Key Points");
  addAccentBar(slide, pres, theme, 0.58, 1.28, 4.9);
  if (spec.kicker) {
    slide.addText(spec.kicker, { x: 0.78, y: 1.2, w: 8.5, h: 0.38, margin: 0, fontFace: theme.fonts.body, fontSize: 15, color: theme.colors.muted, fit: "shrink" });
  }
  addBullets(slide, theme, spec.items || [], 0.8, 1.78, 7.2, 4.45, { fontSize: 20 });
  addCard(slide, pres, theme, 9.05, 1.45, 3.2, 4.7, { fill: theme.colors.primary, line: theme.colors.primary });
  await addIconBubble(slide, pres, theme, spec.icon || "FaLightbulb", 10.25, 2.2, 0.96, { fill: theme.colors.accent });
  slide.addText(spec.visualText || "Signal\nnot noise", { x: 9.45, y: 3.5, w: 2.38, h: 0.9, margin: 0, align: "center", fontFace: theme.fonts.heading, fontSize: 24, bold: true, color: theme.colors.inverse, fit: "shrink" });
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildTwoColumnSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Comparison");
  const columns = [spec.left || {}, spec.right || {}];
  const xs = [0.78, 6.88];
  for (let index = 0; index < columns.length; index += 1) {
    const column = columns[index];
    addCard(slide, pres, theme, xs[index], 1.42, 5.55, 4.88, { fill: theme.colors.surface, line: index === 0 ? theme.colors.primary : theme.colors.accent });
    slide.addText(column.heading || (index === 0 ? "Option A" : "Option B"), {
      x: xs[index] + 0.32,
      y: 1.72,
      w: 4.85,
      h: 0.42,
      margin: 0,
      fontFace: theme.fonts.heading,
      fontSize: 22,
      bold: true,
      color: index === 0 ? theme.colors.primary : theme.colors.accent,
    });
    addBullets(slide, theme, column.items || [], xs[index] + 0.35, 2.38, 4.72, 3.25, { fontSize: 16 });
  }
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildProcessSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Process");
  const steps = spec.steps || [];
  const gap = 0.22;
  const width = (LAYOUT.width - LAYOUT.margin * 2 - gap * (steps.length - 1)) / Math.max(steps.length, 1);
  for (let index = 0; index < steps.length; index += 1) {
    const x = LAYOUT.margin + index * (width + gap);
    addCard(slide, pres, theme, x, 1.6, width, 4.62, { fill: index % 2 === 0 ? theme.colors.surface : "ECFEFF", line: theme.colors.line });
    await addIconBubble(slide, pres, theme, steps[index].icon || "FaCircle", x + 0.28, 1.92, 0.58, { fill: index === steps.length - 1 ? theme.colors.accent : theme.colors.primary });
    slide.addText(String(index + 1).padStart(2, "0"), { x: x + width - 0.75, y: 1.82, w: 0.42, h: 0.24, margin: 0, fontFace: theme.fonts.heading, fontSize: 12, bold: true, color: theme.colors.muted, align: "right" });
    slide.addText(steps[index].title || `Step ${index + 1}`, { x: x + 0.28, y: 2.78, w: width - 0.56, h: 0.36, margin: 0, fontFace: theme.fonts.heading, fontSize: 18, bold: true, color: theme.colors.text, fit: "shrink" });
    slide.addText(steps[index].body || "", { x: x + 0.28, y: 3.28, w: width - 0.56, h: 1.75, margin: 0, fontFace: theme.fonts.body, fontSize: 13, color: theme.colors.muted, fit: "shrink", breakLine: false });
  }
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildIconGridSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Concepts");
  const items = spec.items || [];
  const columns = spec.columns || (items.length > 4 ? 3 : 2);
  const cardW = (LAYOUT.width - LAYOUT.margin * 2 - 0.28 * (columns - 1)) / columns;
  const cardH = 1.55;
  for (let index = 0; index < items.length; index += 1) {
    const row = Math.floor(index / columns);
    const col = index % columns;
    const x = LAYOUT.margin + col * (cardW + 0.28);
    const y = 1.35 + row * (cardH + 0.26);
    addCard(slide, pres, theme, x, y, cardW, cardH, { fill: theme.colors.surface, line: theme.colors.line });
    await addIconBubble(slide, pres, theme, items[index].icon || "FaCheck", x + 0.24, y + 0.31, 0.52, { fill: theme.colors.primary });
    slide.addText(items[index].title || "Item", { x: x + 0.92, y: y + 0.26, w: cardW - 1.12, h: 0.28, margin: 0, fontFace: theme.fonts.heading, fontSize: 15, bold: true, color: theme.colors.text, fit: "shrink" });
    slide.addText(items[index].body || "", { x: x + 0.92, y: y + 0.66, w: cardW - 1.12, h: 0.55, margin: 0, fontFace: theme.fonts.body, fontSize: 11.5, color: theme.colors.muted, fit: "shrink" });
  }
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildQuoteSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "BLANK" });
  slide.background = { color: theme.colors.surface };
  addAccentBar(slide, pres, theme, 0.82, 1.08, 5.45, theme.colors.accent);
  slide.addText(spec.quote || "Quote text", { x: 1.12, y: 1.28, w: 10.6, h: 2.25, margin: 0, fontFace: theme.fonts.heading, fontSize: 34, bold: true, color: theme.colors.text, fit: "shrink", breakLine: false });
  if (spec.attribution) {
    slide.addText(spec.attribution, { x: 1.16, y: 4.02, w: 7.8, h: 0.34, margin: 0, fontFace: theme.fonts.body, fontSize: 14, italic: true, color: theme.colors.muted });
  }
  await addIconBubble(slide, pres, theme, spec.icon || "FaQuoteRight", 10.85, 5.62, 0.62, { fill: theme.colors.primary });
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildChartSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Chart");
  const data = (spec.series || []).map((series) => ({ name: series.name || "Series", labels: spec.labels || [], values: series.values || [] }));
  addCard(slide, pres, theme, 0.78, 1.28, 11.75, 5.35, { fill: theme.colors.surface, line: theme.colors.line });
  slide.addChart(chartType(pres, spec.chartType), data, {
    x: 1.12,
    y: 1.7,
    w: 11.05,
    h: 4.45,
    showTitle: false,
    showLegend: data.length > 1,
    legendPos: "b",
    chartColors: [theme.colors.primary, theme.colors.accent, theme.colors.secondary],
    chartArea: { fill: { color: theme.colors.surface }, border: { color: theme.colors.surface } },
    catAxisLabelColor: theme.colors.muted,
    valAxisLabelColor: theme.colors.muted,
    valGridLine: { color: "E2E8F0", size: 0.5 },
    catGridLine: { style: "none" },
    showValue: spec.showValue !== false,
    dataLabelPosition: "outEnd",
    dataLabelColor: theme.colors.text,
    lineSize: 2.5,
    lineSmooth: true,
    barDir: "col",
  });
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildTableSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Table");
  const rows = [spec.headers || [], ...(spec.rows || [])];
  const tableRows = rows.map((row, rowIndex) => row.map((cell) => ({
    text: String(cell),
    options: rowIndex === 0 ? { bold: true, color: theme.colors.inverse, fill: { color: theme.colors.primary } } : { color: theme.colors.text },
  })));
  slide.addTable(tableRows, {
    x: 0.78,
    y: 1.45,
    w: 11.76,
    h: 4.85,
    margin: 0.08,
    border: { color: theme.colors.line, pt: 0.75 },
    fontFace: theme.fonts.body,
    fontSize: 12.5,
    color: theme.colors.text,
    valign: "mid",
  });
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildImageSlide(pres, theme, spec, deckTitle) {
  const slide = pres.addSlide({ masterName: "CONTENT" });
  addHeader(slide, pres, theme, spec.title || "Image");
  const image = spec.image || {};
  if (!image.path && !image.data) {
    addCard(slide, pres, theme, 0.9, 1.45, 7.4, 4.85, { fill: "E2E8F0", line: theme.colors.line });
    slide.addText("Image missing", { x: 0.9, y: 3.55, w: 7.4, h: 0.36, margin: 0, align: "center", fontFace: theme.fonts.heading, fontSize: 20, color: theme.colors.muted });
  } else {
    slide.addImage({ path: image.path, data: image.data, x: 0.78, y: 1.38, w: 7.95, h: 4.95, sizing: { type: image.sizing || "cover", w: 7.95, h: 4.95 }, altText: image.altText || spec.title || "Slide image" });
  }
  if (spec.body) {
    addCard(slide, pres, theme, 9.08, 1.55, 3.18, 4.48, { fill: theme.colors.surface, line: theme.colors.line });
    slide.addText(spec.body, { x: 9.38, y: 1.95, w: 2.58, h: 3.55, margin: 0, fontFace: theme.fonts.body, fontSize: 15, color: theme.colors.text, fit: "shrink", breakLine: false });
  }
  addFooter(slide, theme, deckTitle);
  addNotes(slide, spec.notes);
}

async function buildClosingSlide(pres, theme, spec) {
  const slide = pres.addSlide({ masterName: "TITLE_DARK" });
  slide.background = { color: theme.colors.primary };
  slide.addText(spec.title || "Thank you", { x: 0.82, y: 2.2, w: 9.3, h: 0.9, margin: 0, fontFace: theme.fonts.heading, fontSize: 44, bold: true, color: theme.colors.inverse, fit: "shrink" });
  if (spec.subtitle) {
    slide.addText(spec.subtitle, { x: 0.86, y: 3.35, w: 8.6, h: 0.55, margin: 0, fontFace: theme.fonts.body, fontSize: 18, color: theme.colors.inverse, transparency: 8 });
  }
  await addIconBubble(slide, pres, theme, spec.icon || "FaArrowRight", 10.68, 2.52, 1.0, { fill: theme.colors.accent });
  addNotes(slide, spec.notes);
}

async function buildSlide(pres, theme, slideSpec, deckTitle) {
  switch (slideSpec.type || "bullets") {
    case "title":
      return buildTitleSlide(pres, theme, slideSpec);
    case "section":
      return buildSectionSlide(pres, theme, slideSpec);
    case "twoColumn":
    case "comparison":
      return buildTwoColumnSlide(pres, theme, slideSpec, deckTitle);
    case "process":
      return buildProcessSlide(pres, theme, slideSpec, deckTitle);
    case "iconGrid":
      return buildIconGridSlide(pres, theme, slideSpec, deckTitle);
    case "quote":
      return buildQuoteSlide(pres, theme, slideSpec, deckTitle);
    case "chart":
      return buildChartSlide(pres, theme, slideSpec, deckTitle);
    case "table":
      return buildTableSlide(pres, theme, slideSpec, deckTitle);
    case "image":
      return buildImageSlide(pres, theme, slideSpec, deckTitle);
    case "closing":
      return buildClosingSlide(pres, theme, slideSpec);
    case "bullets":
    default:
      return buildBulletsSlide(pres, theme, slideSpec, deckTitle);
  }
}

async function createDeck(spec, outputPath) {
  const theme = normalizeThemeColors(mergeTheme(spec.theme));
  const pres = new pptxgen();
  pres.layout = spec.layout || "LAYOUT_WIDE";
  pres.author = spec.author || "GitHub Copilot";
  pres.subject = spec.subject || spec.title || "Presentation";
  pres.title = spec.title || "Presentation";
  pres.company = spec.company || "";
  pres.lang = spec.lang || "en-US";
  pres.theme = {
    headFontFace: theme.fonts.heading,
    bodyFontFace: theme.fonts.body,
    lang: pres.lang,
  };
  defineMasters(pres, theme);
  const slides = spec.slides && spec.slides.length ? spec.slides : SAMPLE_SPEC.slides;
  for (const slideSpec of slides) {
    await buildSlide(pres, theme, slideSpec, spec.title);
  }
  await pres.writeFile({ fileName: outputPath });
}

async function main() {
  const args = process.argv.slice(2);
  if (args[0] === "--sample") {
    const samplePath = args[1];
    if (!samplePath) {
      usage();
      process.exit(1);
    }
    fs.mkdirSync(path.dirname(path.resolve(samplePath)), { recursive: true });
    fs.writeFileSync(samplePath, `${JSON.stringify(SAMPLE_SPEC, null, 2)}\n`, "utf8");
    console.log(JSON.stringify({ ok: true, sample: samplePath }, null, 2));
    return;
  }

  if (args.length < 2) {
    usage();
    process.exit(1);
  }
  const specPath = path.resolve(args[0]);
  const outputPath = path.resolve(args[1]);
  const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
  await createDeck(spec, outputPath);
  console.log(JSON.stringify({ ok: true, output: outputPath }, null, 2));
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: error.message, stack: error.stack }, null, 2));
  process.exit(1);
});