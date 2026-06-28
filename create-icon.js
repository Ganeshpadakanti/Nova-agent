// Run this once with: node create-icon.js
// It makes a simple purple "N" icon for the system tray

const { createCanvas } = require('canvas')
const fs = require('fs')
const path = require('path')

try {
  const size = 32
  const canvas = createCanvas(size, size)
  const ctx = canvas.getContext('2d')

  // Purple circle background
  ctx.fillStyle = '#7c3aed'
  ctx.beginPath()
  ctx.arc(16, 16, 15, 0, Math.PI * 2)
  ctx.fill()

  // White "N" letter
  ctx.fillStyle = 'white'
  ctx.font = 'bold 18px Arial'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('N', 16, 17)

  const buffer = canvas.toBuffer('image/png')
  fs.writeFileSync(path.join(__dirname, 'assets', 'tray-icon.png'), buffer)
  console.log('Icon created: assets/tray-icon.png')
} catch (e) {
  console.log('Could not generate icon (canvas not installed). App will still run without a custom tray icon.')
}