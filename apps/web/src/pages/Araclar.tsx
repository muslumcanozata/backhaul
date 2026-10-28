import { FormEvent, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CardHeader from "@mui/material/CardHeader";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import { useFleet } from "../fleet-data";
import { STATUS_LABEL, TRAILER_LABEL, availability, canWriteMaster, driverName } from "../labels";
import { useSession } from "../session";
import { VehicleFile } from "./VehicleFile";

export function Araclar() {
  const { token, user, notice } = useSession();
  const { vehicles, drivers, settings, reload } = useFleet();
  const [selected, setSelected] = useState("");
  const [plate, setPlate] = useState("");
  const [capacity, setCapacity] = useState("24");
  const [trailer, setTrailer] = useState(settings?.enabled_trailer_types[0] ?? "tenteli");
  const vehicle = vehicles.find((item) => item.id === selected);
  const types = settings?.enabled_trailer_types ?? ["tenteli"];

  useEffect(() => {
    if (!types.includes(trailer)) setTrailer(types[0]);
  }, [types, trailer]);

  async function create(event: FormEvent) {
    event.preventDefault();
    notice("");
    try {
      const created = await api<{ id: string }>("/vehicles", token, {
        method: "POST",
        body: JSON.stringify({ plate, capacity_tons: capacity, trailer_type: trailer }),
      });
      setPlate("");
      setSelected(created.id);
      await reload();
    } catch (err) {
      notice(err instanceof Error ? err.message : "Araç eklenemedi");
    }
  }

  return (
    <Box sx={{ display: "grid", gap: 3, gridTemplateColumns: { xs: "1fr", lg: canWriteMaster(user.role) ? "1.4fr 0.8fr" : "1fr" } }}>
      <Card>
        <CardHeader title="Araçlar" subheader={vehicle ? "Dosya sağdan açılır." : "Dosya için bir araç seçin."} />
        <List>
          {vehicles.map((item) => (
            <ListItemButton key={item.id} selected={item.id === selected} onClick={() => setSelected(item.id)}>
              <Stack>
                <Typography variant="subtitle2">{item.plate}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {TRAILER_LABEL[item.trailer_type] ?? item.trailer_type} · {item.capacity_tons} ton · {STATUS_LABEL[item.status] ?? item.status} ·{" "}
                  {driverName(drivers, item.driver_id)} · {availability(item, settings)}
                </Typography>
              </Stack>
            </ListItemButton>
          ))}
        </List>
        {vehicles.length === 0 ? (
          <CardContent>
            <Typography color="text.secondary">Kayıtlı araç yok.</Typography>
          </CardContent>
        ) : null}
      </Card>
      {canWriteMaster(user.role) ? (
        <Card component="form" onSubmit={create}>
          <CardHeader title="Araç ekle" />
          <CardContent>
            <Stack spacing={2}>
              <TextField label="Plaka" value={plate} onChange={(event) => setPlate(event.target.value)} required />
              <TextField label="Kapasite (ton)" value={capacity} onChange={(event) => setCapacity(event.target.value)} required />
              <TextField select label="Kasa" value={types.includes(trailer) ? trailer : types[0]} onChange={(event) => setTrailer(event.target.value)}>
                {types.map((type) => (
                  <MenuItem key={type} value={type}>
                    {TRAILER_LABEL[type] ?? type}
                  </MenuItem>
                ))}
              </TextField>
              <Button type="submit" variant="contained">
                Ekle
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : null}
      {vehicle ? <VehicleFile vehicle={vehicle} drivers={drivers} settings={settings} onChanged={reload} onClose={() => setSelected("")} /> : null}
    </Box>
  );
}
