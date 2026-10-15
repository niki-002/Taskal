interface ReloadButtonProps {
  onClick: () => void
}

export function ReloadButton({ onClick }: ReloadButtonProps) {
  return (
    <button id="reload_button" className="button" type="button" onClick={onClick}>
      再読み込み
    </button>
  )
}
