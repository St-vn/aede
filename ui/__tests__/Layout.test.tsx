import React from 'react'
import { render, screen } from '@testing-library/react'
import { Layout } from '../components/Layout'

test('renders sidebar and center pane slots', () => {
  render(
    <Layout
      sidebar={<div data-testid="sb">Sidebar</div>}
      centerPane={<div data-testid="cp">Center</div>}
    />
  )
  expect(screen.getByTestId('sb')).toBeInTheDocument()
  expect(screen.getByTestId('cp')).toBeInTheDocument()
})

test('root container has h-dvh class', () => {
  const { container } = render(<Layout sidebar={<div />} centerPane={<div />} />)
  expect((container.firstChild as HTMLElement).className).toContain('h-dvh')
})

test('center pane has flex-1', () => {
  render(<Layout sidebar={<div />} centerPane={<div data-testid="cp" />} />)
  const cp = screen.getByTestId('cp').parentElement
  expect(cp?.className).toContain('flex-1')
})
