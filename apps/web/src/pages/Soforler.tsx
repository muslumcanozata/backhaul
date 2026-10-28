import { FormEvent, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { canWriteMaster } from "../labels";
import { useSession } from "../session";

export function Soforler() {
  const { token, user, notice } = useSession();
  const { vehicles, drivers, reload } = useFleet();
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [card, setCard] = useState("");
  const driver = drivers.find((item) => item.id === selected);
  const vehicle = vehicles.find((item) => item.driver_id === driver?.id);

  async function create(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      const created = await api<{ id: string }>("/drivers", token, {
        method: "POST",
        body: JSON.stringify({ name, phone, card_id: card || null }),
      });
      setName("");
      setPhone("");
      setCard("");
      setSelected(created.id);
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Şoför eklenemedi");
    }
  }

  return (
    <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" } }}>
      <Stack spacing={3}>
        <Card>
          <CardHeader title="Şoförler" />
          <List>
            {drivers.map((item) => {
              const bound = vehicles.find((row) => row.driver_id === item.id);
              return (
                <ListItemButton key={item.id} selected={item.id === selected} onClick={() => setSelected(item.id)}>
                  <Stack>
                    <Typography variant="subtitle2">{item.name}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {item.phone} · {bound ? bound.plate : "Araç yok"}
                    </Typography>
                  </Stack>
                </ListItemButton>
              );
            })}
          </List>
          {drivers.length === 0 ? (
            <CardContent>
              <Typography color="text.secondary">Kayıtlı şoför yok.</Typography>
            </CardContent>
          ) : null}
        </Card>
        {canWriteMaster(user.role) ? (
          <Card component="form" onSubmit={create}>
            <CardHeader title="Şoför ekle" />
            <CardContent>
              <Stack spacing={2}>
                <TextField label="Ad" value={name} onChange={(event) => setName(event.target.value)} required />
                <TextField label="Telefon" value={phone} onChange={(event) => setPhone(event.target.value)} required />
                <TextField label="Kart" value={card} onChange={(event) => setCard(event.target.value)} />
                <Button type="submit" variant="contained">
                  Ekle
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}
      </Stack>
      <Card>
        <CardHeader title={driver?.name ?? "Şoför dosyası"} subheader={driver ? "SMS geçmişi rota bildirimleri açılınca bu dosyada durur." : "Dosya için bir şoför seçin."} />
        {driver ? (
          <CardContent>
            <Stack spacing={1.5}>
              <div>
                <Typography variant="caption" color="text.secondary">
                  Telefon
                </Typography>
                <Typography>{driver.phone}</Typography>
              </div>
              <div>
                <Typography variant="caption" color="text.secondary">
                  Kart
                </Typography>
                <Typography>{driver.card_id ?? "Yok"}</Typography>
              </div>
              <div>
                <Typography variant="caption" color="text.secondary">
                  Araç
                </Typography>
                <Typography>{vehicle ? vehicle.plate : "Bağlı araç yok"}</Typography>
              </div>
            </Stack>
          </CardContent>
        ) : null}
      </Card>
    </Box>
  );
}
