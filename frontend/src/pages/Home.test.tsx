import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Home from './Home'

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>
  )
}

describe('Home', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('locks upload until requirements are saved', () => {
    renderHome()

    const fileInput = screen.getByLabelText('book file')
    expect(fileInput).toBeDisabled()

    const saveBtn = screen.getByRole('button', { name: '保存并进入上传' })
    fireEvent.click(saveBtn)

    expect(screen.getByRole('button', { name: '已保存' })).toBeInTheDocument()
    expect(screen.getByLabelText('book file')).not.toBeDisabled()
  })
})
