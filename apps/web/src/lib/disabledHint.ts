export const disabledHintProps = (message?: string) =>
  message
    ? {
        'data-disabled-hint': message,
        tabIndex: 0,
      }
    : {};