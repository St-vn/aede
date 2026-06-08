import { test, expect } from '@playwright/test'

test('dark background CSS variable is set', async ({ page }) => {
  await page.goto('/')
  const bg = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--background').trim()
  )
  expect(bg).toBe('5 5 8')
})

test('brand primary CSS variable is correct', async ({ page }) => {
  await page.goto('/')
  const primary = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()
  )
  expect(primary).toBe('94 106 210')
})

test('warning color is amber (gate-only)', async ({ page }) => {
  await page.goto('/')
  const warning = await page.evaluate(() =>
    getComputedStyle(document.documentElement).getPropertyValue('--color-warning').trim()
  )
  expect(warning).toBe('240 160 32')
})
