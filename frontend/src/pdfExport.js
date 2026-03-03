/**
 * PDF Export — Daily Lesson Plan (A4, Arial-equivalent, bold labels)
 * Uses jsPDF + jspdf-autotable
 *
 * Key rendering strategy:
 *   willDrawCell → data.cell.text = []  (suppress autoTable's own text draw)
 *   didDrawCell  → draw manually with bold label + normal body
 */
import { jsPDF } from 'jspdf'
import autoTable from 'jspdf-autotable'

// ─── Roman numeral converter ──────────────────────────────────────────────────

const ROMAN_MAP = [
    [1000,'M'],[900,'CM'],[500,'D'],[400,'CD'],
    [100,'C'],[90,'XC'],[50,'L'],[40,'XL'],
    [10,'X'],[9,'IX'],[5,'V'],[4,'IV'],[1,'I']
]
function toRoman(n) {
    if (!n || isNaN(n) || n < 1) return String(n)
    let result = ''
    for (const [val, sym] of ROMAN_MAP) {
        while (n >= val) { result += sym; n -= val }
    }
    return result
}

/** Convert "Grade 2" → "Grade II", leaves other strings unchanged */
function gradeToRoman(grade) {
    if (!grade) return grade
    return grade.replace(/(\d+)/, (_, num) => toRoman(parseInt(num, 10)))
}

// ─── Phase label stripper ─────────────────────────────────────────────────────

/** Remove "Phase N:" / "Phase N -" prefixes and blank Phase-only lines */
function stripPhaseLabels(text) {
    if (!text) return text
    return text
        .split('\n')
        .filter(line => !/^Phase\s+\d+\s*[:\-]?\s*$/i.test(line.trim()))
        .map(line => line.replace(/^Phase\s+\d+\s*[:\-]\s*/i, ''))
        .join('\n')
}

// ─── HTML parser ─────────────────────────────────────────────────────────────

function parseLessonPlanHTML(html) {
    const d = document.createElement('div')
    d.innerHTML = html

    const sections = []
    let currentH2 = null
    let contentNodes = []

    const flush = () => {
        if (currentH2 !== null) sections.push({ title: currentH2, nodes: [...contentNodes] })
        contentNodes = []
    }

    d.childNodes.forEach(node => {
        if (node.nodeType !== Node.ELEMENT_NODE) return
        if (node.tagName.toLowerCase() === 'h2') { flush(); currentH2 = node.textContent.trim() }
        else if (currentH2 !== null) contentNodes.push(node)
    })
    flush()

    const result = {}
    sections.forEach(({ title, nodes }) => {
        const lines = []
        nodes.forEach(node => {
            const tag = node.tagName?.toLowerCase()
            if (tag === 'ul' || tag === 'ol') {
                node.querySelectorAll('li').forEach(li => lines.push('\u2022 ' + li.textContent.trim()))
            } else {
                const t = node.textContent?.trim()
                if (t) lines.push(t)
            }
        })
        result[title] = lines.join('\n')
    })
    return result
}

function findSection(sections, ...keywords) {
    const key = Object.keys(sections).find(k =>
        keywords.some(kw => k.toLowerCase().includes(kw.toLowerCase()))
    )
    return key ? sections[key] : ''
}

// ─── Manual cell text renderer ────────────────────────────────────────────────

const FONT   = 'helvetica'
const SZ     = 12       // pt
const PAD_T  = 1.5      // cell padding top/bottom mm
const PAD_LR = 2        // cell padding left/right mm

/** pt → mm */
const ptToMm = pt => pt * 0.352778
/** Line height in mm */
const lineH  = () => ptToMm(SZ) * 1.4

/**
 * Calculate the total rendered height (mm) for a given content string
 * at a given inner cell width. Mirrors drawCellContent logic exactly.
 */
function calcCellHeight(doc, rawContent, innerW) {
    if (!rawContent) return PAD_T * 2 + lineH()
    const lh    = lineH()
    let   lines = 0

    rawContent.split('\n').forEach((line, idx) => {
        if (!line) { lines++; return }

        const colonIdx    = line.indexOf(':')
        const hasColon    = colonIdx > 0
        const normalAfter = hasColon ? line.substring(colonIdx + 1) : ''
        const boldWhole   = idx === 0 && ((hasColon && !normalAfter.trim()) || (!hasColon && /^(\d+\.|[A-Z])/.test(line)))
        // Only bold "Label: value" when colon is short prefix (≤40 chars) and not a bullet line
        const isBoldLabel = hasColon && normalAfter.trim() && colonIdx <= 40 && !line.trimStart().startsWith('\u2022')

        if (boldWhole) {
            doc.setFont(FONT, 'bold'); doc.setFontSize(SZ)
            lines += doc.splitTextToSize(line, innerW).length
        } else if (isBoldLabel) {
            doc.setFont(FONT, 'bold'); doc.setFontSize(SZ)
            const boldW = doc.getTextWidth(line.substring(0, colonIdx + 1))
            doc.setFont(FONT, 'normal'); doc.setFontSize(SZ)
            lines += doc.splitTextToSize(normalAfter, innerW - boldW).length
        } else {
            doc.setFont(FONT, 'normal'); doc.setFontSize(SZ)
            lines += doc.splitTextToSize(line, innerW).length
        }
    })

    return PAD_T * 2 + lines * lh
}

/**
 * Draw cell content with bold "Label:" on any line that has a colon.
 * Called from didDrawCell — autoTable text has already been suppressed.
 */
function drawCellContent(doc, cell, rawContent) {
    if (!rawContent) return

    const innerW = cell.width - PAD_LR * 2

    let x = cell.x + PAD_LR
    let y = cell.y + PAD_T + ptToMm(SZ) * 0.85   // baseline offset from top padding

    const lh = lineH()

    const lines = rawContent.split('\n')

    lines.forEach((line, idx) => {
        if (!line) { y += lh; return }

        const colonIdx = line.indexOf(':')

        // Bold "Label:" pattern on every line that has a colon.
        // Additionally bold the whole first line when it looks like a heading.
        const hasColon    = colonIdx > 0
        const normalAfter = hasColon ? line.substring(colonIdx + 1).trim() : ''
        const boldWholeLine = idx === 0 && (
            (hasColon && !normalAfter) ||           // "1. Read and listen:"  or "Lesson Evaluation:"
            (!hasColon && /^(\d+\.|[A-Z])/.test(line))  // "Talk about it" style (capitalised / numbered)
        )
        // Only bold "Label: value" when colon is a short label prefix (≤40 chars) and not a bullet
        const isBoldLabel = hasColon && normalAfter && colonIdx <= 40 && !line.trimStart().startsWith('\u2022')

        if (boldWholeLine) {
            // Entire first line bold (exercise heading or label with no body on same line)
            doc.setFont(FONT, 'bold')
            doc.setFontSize(SZ)
            const wrapped = doc.splitTextToSize(line, innerW)
            wrapped.forEach(wl => { doc.text(wl, x, y); y += lh })

        } else if (isBoldLabel) {
            // First line: bold "Label:" + normal rest on same line
            const boldPart   = line.substring(0, colonIdx + 1)
            const normalPart = line.substring(colonIdx + 1)

            doc.setFont(FONT, 'bold')
            doc.setFontSize(SZ)
            const boldW = doc.getTextWidth(boldPart)
            doc.text(boldPart, x, y)

            doc.setFont(FONT, 'normal')
            doc.setFontSize(SZ)
            const wrapped = doc.splitTextToSize(normalPart, innerW - boldW)
            wrapped.forEach((wl, wi) => {
                doc.text(wl, x + (wi === 0 ? boldW : 0), y + wi * lh)
            })
            y += wrapped.length * lh

        } else {
            // Normal line (body text, bullets, fixed statements)
            doc.setFont(FONT, 'normal')
            doc.setFontSize(SZ)
            const wrapped = doc.splitTextToSize(line, innerW)
            wrapped.forEach(wl => { doc.text(wl, x, y); y += lh })
        }
    })
}

// ─── Main export ──────────────────────────────────────────────────────────────

function buildPDF(htmlContent, meta) {
    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })

    const pageW  = doc.internal.pageSize.getWidth()   // 210
    const marginL = 10
    const marginR = 10
    const tableW  = pageW - marginL - marginR

    // ── Parse HTML ────────────────────────────────────────────────────────────
    const sections = parseLessonPlanHTML(htmlContent)

    const slos        = findSection(sections, 'SLO')
    const skills      = findSection(sections, 'Skills Focused On', 'Skills')
    const resources   = findSection(sections, 'Resources')
    const methodology = findSection(sections, 'Methodology')
    const recall      = findSection(sections, 'Recall', 'Recap')
    const vocabulary  = findSection(sections, 'Vocabulary')
    const warmup      = findSection(sections, 'Warm-up', 'Warm up', 'Warmup')
    const diffInstr   = findSection(sections, 'Differentiated')
    const extension   = findSection(sections, 'Extension')
    const successCrit = findSection(sections, 'Success Criteria')
    const aflRaw      = findSection(sections, 'AFL')
    const classwork   = findSection(sections, 'Classwork', 'C.W')
    const homework    = findSection(sections, 'Homework', 'H.W')
    const online      = findSection(sections, 'Online Assignment')
    const wrapup      = findSection(sections, 'Wrap Up', 'Plenary')

    // Strip the fixed intro statement from all section content so it only
    // appears once via the hardcoded row below.
    const INTRO_STMT = 'introduce the topic and share the slos with the students'
    const stripIntro = (text) => {
        if (!text) return text
        return text
            .split('\n')
            .filter(line => !line.toLowerCase().includes(INTRO_STMT))
            .join('\n')
    }
    Object.keys(sections).forEach(k => { sections[k] = stripIntro(sections[k]) })

    // Exercise sections — anything not matching a fixed section key
    const knownTitles = [
        'slo', 'skills focused', 'resources', 'methodology', 'recap', 'recall',
        'vocabulary', 'warm-up', 'warm up', 'warmup', 'differentiated',
        'extension', 'success criteria', 'afl', 'classwork', 'c.w', 'homework',
        'h.w', 'online assignment', 'wrap up', 'plenary'
    ]
    const exerciseSections = Object.entries(sections).filter(([title]) =>
        !knownTitles.some(k => title.toLowerCase().includes(k))
    )

    // ── Meta ──────────────────────────────────────────────────────────────────
    const grade    = meta?.grade || ''
    const subject  = meta?.subject || ''
    const lessonNo = meta?.lessonNumber || ''
    const gradeRoman = gradeToRoman(grade)
    const topicStr = meta?.topic || [grade, subject, lessonNo ? `Lesson ${lessonNo}` : ''].filter(Boolean).join(' \u2014 ')

    // AFL: strip descriptions — keep only the strategy name (text before first ":")
    const aflNames = aflRaw
        .split('\n')
        .map(line => {
            const stripped = line.replace(/^\u2022\s*/, '').trim()
            const ci = stripped.indexOf(':')
            return ci > 0 ? stripped.substring(0, ci).trim() : stripped
        })
        .filter(Boolean)
        .join(', ')

    // Success Criteria body
    const successBody = successCrit
        ? (successCrit.startsWith('Remember to') ? successCrit : `Remember to:\n${successCrit}`)
        : 'Remember to:'

    // ── Header (above table) ──────────────────────────────────────────────────
    let y = 12
    doc.setFont(FONT, 'bold')
    doc.setFontSize(SZ + 4)
    doc.text('Army Public Schools & Colleges System', pageW / 2, y, { align: 'center' })

    y += 6
    doc.setFont(FONT, 'bold')
    doc.setFontSize(SZ + 1)
    doc.text('Daily Lesson Plan', pageW / 2, y, { align: 'center' })

    y += 6
    doc.setFont(FONT, 'normal')
    doc.setFontSize(SZ)
    doc.text('Week: ___________', marginL, y)
    doc.text('Developed by: ___________', pageW - marginR, y, { align: 'right' })

    y += 5
    doc.text('Date: ___________', marginL, y)
    doc.text('Taught by: ___________', pageW - marginR, y, { align: 'right' })

    y += 4

    // ── Build table rows ──────────────────────────────────────────────────────
    // Helper: full-width cell
    const fw = (content, extraStyles = {}) => ([{
        content,
        colSpan: 2,
        styles: { halign: 'left', ...extraStyles }
    }])

    // Skills + Resources combined (SOW Pages appended decoratively)
    const skillsResLine = skills ? `Skills focused on: ${skills}` : ''
    const sowPagesLine  = meta?.sowPages ? `SOW Pages: ${meta.sowPages}` : ''
    const resourcesLine = [resources ? `Resources: ${resources}` : '', sowPagesLine].filter(Boolean).join('\n')
    const skillsResources = [skillsResLine, resourcesLine].filter(Boolean).join('\n')

    const tableRows = []

    // Row 1: Class (roman numeral grade) | Subject
    tableRows.push([
        { content: `Class: ${gradeRoman}`, styles: { halign: 'left' } },
        { content: `Subject: ${subject}`,  styles: { halign: 'left' } }
    ])
    // Row 2: Period | Topic (lesson name)
    tableRows.push([
        { content: 'Period: 1',          styles: { halign: 'left' } },
        { content: `Topic: ${topicStr}`, styles: { halign: 'left' } }
    ])

    // SLOs
    tableRows.push(fw(`SLO(s): Students will be able to\n${stripPhaseLabels(slos)}`))

    // Skills + Resources
    if (skillsResources.trim()) tableRows.push(fw(stripPhaseLabels(skillsResources)))

    // Methodology
    if (methodology) tableRows.push(fw(`Methodology: ${stripPhaseLabels(methodology)}`))

    // Recall
    if (recall) tableRows.push(fw(`Recap / Recall: ${stripPhaseLabels(recall)}`))

    // Vocabulary
    if (vocabulary) tableRows.push(fw(`Vocabulary: ${stripPhaseLabels(vocabulary)}`))

    // Fixed intro statement
    tableRows.push(fw('Introduce the topic and share the SLOs with the students.'))

    // Warm-up
    if (warmup) tableRows.push(fw(`Warm-up: ${stripPhaseLabels(warmup)}`))

    // Exercises — skip sections that are only a Phase label, strip Phase prefix from titles
    exerciseSections
        .filter(([title]) => !/^Phase\s+\d+\s*[:\-]?\s*$/i.test(title.trim()))
        .forEach(([title, content]) => {
            const cleanTitle = title.replace(/^Phase\s+\d+\s*[:\-]\s*/i, '').trim()
            const cleanContent = stripPhaseLabels(content)
            tableRows.push(fw(cleanContent ? `${cleanTitle}\n${cleanContent}` : cleanTitle))
        })

    // Differentiated
    if (diffInstr) tableRows.push(fw(`Differentiated Instruction: ${diffInstr}`))

    // Extension
    if (extension) tableRows.push(fw(`Extension Activity: ${extension}`))

    // Share success criteria (fixed statement)
    tableRows.push(fw('Share the success criteria with the students.'))

    // Success Criteria
    tableRows.push(fw(`Success Criteria:\n${successBody}`))

    // AFL — names only
    if (aflNames) tableRows.push(fw(`AFL Strategies: ${aflNames}`))

    // Classwork
    if (classwork) tableRows.push(fw(`C.W: ${classwork}`))

    // Homework
    tableRows.push(fw(`H.W: ${homework || 'Nil'}`))

    // Online
    tableRows.push(fw(`Online Assignment (if any): ${online || 'Nil'}`))

    // Plenary/Wrap Up
    tableRows.push(fw(`Plenary/Wrap Up: ${wrapup || ''}`))

    // Lesson Evaluation — tall blank cell
    tableRows.push(fw('Lesson Evaluation:', { minCellHeight: 22 }))

    // ── Render table ──────────────────────────────────────────────────────────
    autoTable(doc, {
        startY: y,
        tableWidth: tableW,
        margin: { left: marginL, right: marginR },
        theme: 'grid',
        rowPageBreak: 'avoid',
        styles: {
            font: FONT,
            fontSize: SZ,
            cellPadding: { top: PAD_T, right: PAD_LR, bottom: PAD_T, left: PAD_LR },
            overflow: 'linebreak',
            valign: 'top',
            lineColor: [0, 0, 0],
            lineWidth: 0.3,
            textColor: [0, 0, 0],
        },
        columnStyles: {
            0: { cellWidth: tableW / 2 },
            1: { cellWidth: tableW / 2 }
        },
        body: tableRows,

        // STEP 1: force correct cell height before autoTable locks in dimensions
        didParseCell(data) {
            if (data.section !== 'body') return
            const raw = data.cell.raw?.content
            if (raw == null) return
            const colSpan = data.cell.raw?.colSpan || 1
            const innerW  = (tableW / 2) * colSpan - PAD_LR * 2
            const needed  = calcCellHeight(doc, raw, innerW)
            // Also respect any explicit minCellHeight set on the cell (e.g. Lesson Evaluation)
            const existing = data.cell.styles.minCellHeight || 0
            data.cell.styles.minCellHeight = Math.max(needed, existing)
        },

        // STEP 2: suppress autoTable's own text rendering
        willDrawCell(data) {
            if (data.section === 'body') data.cell.text = []
        },

        // STEP 3: draw manually with bold labels
        didDrawCell(data) {
            if (data.section !== 'body') return
            const raw = data.cell.raw?.content
            if (raw == null) return
            drawCellContent(doc, data.cell, raw)
        }
    })

    // ── Signature line (left-aligned, just below table) ───────────────────────
    const tableEndY = doc.lastAutoTable.finalY + 5
    doc.setFont(FONT, 'bold')
    doc.setFontSize(SZ)
    doc.text('Sign / Name & Date:  Subject Coordinator: _________________________', marginL, tableEndY + lineH() * 2)

    // ── "Designed by Teravox" fixed at bottom of every page ───────────────────
    const pageH      = doc.internal.pageSize.getHeight()
    const footerY    = pageH - 6
    const totalPages = doc.internal.getNumberOfPages()
    for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i)
        doc.setFont(FONT, 'normal')
        doc.setFontSize(SZ - 3)
        doc.text('Designed by Teravox', pageW / 2, footerY, { align: 'center' })
    }

    const fname = `LP_${(grade || 'Grade').replace(/\s+/g, '_')}_${subject}_Lesson${lessonNo || ''}.pdf`
    return { doc, fname }
}

export function downloadLessonPlanPDF(htmlContent, meta) {
    const { doc, fname } = buildPDF(htmlContent, meta)
    doc.autoPrint()
    window.open(doc.output('bloburl'), '_blank')
}
