import { Stack, Toast, Toaster, createToaster } from '@chakra-ui/react'

export const toaster = createToaster({
  placement: 'top-end',
  pauseOnPageIdle: true,
})

export function AppToaster() {
  return (
    <Toaster toaster={toaster}>
      {(toast) => (
        <Toast.Root>
          <Toast.Indicator />
          <Stack gap={1} flex="1" maxWidth="100%">
            {toast.title ? <Toast.Title>{toast.title}</Toast.Title> : null}
            {toast.description ? (
              <Toast.Description>{toast.description}</Toast.Description>
            ) : null}
          </Stack>
          <Toast.CloseTrigger />
        </Toast.Root>
      )}
    </Toaster>
  )
}
