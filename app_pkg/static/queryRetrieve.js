$(document).ready(function () {

    // Initialize devices table
    var devices_table = $('#devices').DataTable({
        ajax: "/get_devices",
        columns: [            
            { data: 'name', title:'Nombre' },
            { data: 'ae_title', title: 'AE Title' },
            { data: 'address', title: 'Dirección' }
        ],
        searching: false,
        paging: false,
        ordering: false,
        info: false,
        initComplete: function() {

            // Select last selected device
            if (localStorage.getItem('sourceDevice') !== null) {
                console.log(localStorage.getItem("sourceDevice"))
                devices_table.row(localStorage.getItem("sourceDevice")).select()
            } else {
                devices_table.row().select()
            }
            initStudiesTable()
            initDestinations()
        },
            
    });

    // Enable select behaviour for device table
    $('#devices tbody').on('click', 'tr', function () {                
        if (!$(this).hasClass('selected')) {                  
            devices_table.rows().deselect()
            devices_table.row($(this)).select()
        }
    });

    // Show last query values in date and modalities selector
    if (localStorage.getItem('dateSelector') !== null ) {
        $("#startDate").val(localStorage.getItem("startDate"))
        $("#endDate").val(localStorage.getItem("endDate"))
        $("#" + localStorage.getItem("dateSelector")).prop("checked", true)
        if (localStorage.getItem("dateSelector") == "day") {
            $('#startDate').prop("disabled", false)
        }
        if (localStorage.getItem("dateSelector") == "between") {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", false)
        }
        JSON.parse(localStorage.modalities).forEach(function(item) {
            $("[name='modality'][value='"+item+"']").prop('checked',true)
        })

    } else {
        $("#today").prop("checked", true)
        document.getElementById('startDate').valueAsDate = new Date()
        document.getElementById('endDate').valueAsDate = new Date()
    }        

    // Enable/disable date pickers
    $("[name='date']").on('click', function(){

        if ($(this)[0].id == 'day') {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", true)
        }
        else if ($(this)[0].id == 'between') {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", false)
        }
        else {
            $('#startDate').prop("disabled", true)
            $('#endDate').prop("disabled", true)
        }
    })

    // Show search field placeholder
    $( "#search-field" ).change(function() {
        var value = $(this).val()
        if (value == "PatientName") {
            $("#search-value").attr("placeholder", "Nombre del paciente");
        }            
        else if (value == "PatientID") {
            $("#search-value").attr("placeholder", "HC/OPI");
        }
        else if (value == "StudyDescription") {
            $("#search-value").attr("placeholder", "Descripción del estudio");
        }

      });
        
    // ------------------ Device manager
    var deviceAction

    // Adapt modal contents depending on selected action
    $("#newDevice").on('click', function () {
        deviceAction = "add"
        // Reset form
        $("#deviceManagerForm")[0].reset()
        $('.modal-title').text('Añadir dispositivo')
        $('#deviceManagerName').prop('disabled', false)
                
    })
    $("#editDevice").on('click', function () {
        deviceAction = "edit"        
        $('.modal-title').text('Editar dispositivo')
        // Fill form with selected device info
        data = devices_table.rows({ selected: true }).data()[0]
        $('#deviceManagerName').prop('disabled',true)
        $('#deviceManagerName').val(data.name)
        $('#deviceManagerAET').val(data.ae_title)
        $('#deviceManagerIP').val(data.address.split(":")[0])
        $('#deviceManagerPort').val(data.address.split(":")[1])
        $('#deviceManagerImgsSeries').val(data.imgs_series)  
        $('#deviceManagerImgsStudy').val(data.imgs_study)     
    })

    // Delete device
    $("#deleteDevice").on('click', function () {

        var ajax_data = devices_table.rows({ selected: true }).data()[0]
        ajax_data.action = "delete"

        $.ajax({
            url: "/manage_devices",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                alert(response.message)
                devices_table.ajax.reload()
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            }); 
    })

    // New/Edit form submit
    $("#deviceManagerForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();        

        var ajax_data = {
            "action": deviceAction,
            "name": $('#deviceManagerName').val(),
            "ae_title":  $('#deviceManagerAET').val(),
            "address": $('#deviceManagerIP').val(),
            "port": $('#deviceManagerPort').val(),
            "imgs_series": $('#deviceManagerImgsSeries').val(),  
            "imgs_study": $('#deviceManagerImgsStudy').val()  
        }

        $.ajax({
            url: "/manage_devices",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                alert(response.message)
                devices_table.ajax.reload()
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });     

    });
    
    // Query for imgs fields
    $(".queryImgsFieldBtn").on('click', function(event) {

        console.log('click')
        event.preventDefault();

        $(".queryImgsFieldBtn").each(function() {
            $(this)[0].innerHTML = `<span class="spinner-border spinner-border-sm"></span>`
            $(this).prop('disabled', true);
        })
        
        var ajax_data = {
            "ae_title":  $('#deviceManagerAET').val(),
            "address": $('#deviceManagerIP').val(),
            "port": $('#deviceManagerPort').val()
        }
        $.ajax({
            url: "/query_imgs_field",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                    
                // Show success message
                $(".queryImgsFieldBtn").each(function() {
                    $(this)[0].innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                  </svg>`
                    $(this).prop('disabled', false);
                })
                $('#deviceManagerImgsStudy').val(response.imgs_study)
                $('#deviceManagerImgsSeries').val(response.imgs_series)                     
                
            },
            error: function(xhr, status, error) {
                // handle error response here
                $(".queryImgsFieldBtn").each(function() {
                    $(this)[0].innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-search" viewBox="0 0 16 16">
                    <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/>
                  </svg>`
                    $(this).prop('disabled', false);
                })
                $('#deviceManagerImgsStudy').val("Unknown")
                $('#deviceManagerImgsSeries').val("Unknown") 
            }
            });   
    })

});

// Initialize studies table
function initStudiesTable() {
    
    var devices_table = $('#devices').DataTable()
    var table_studies = $('#studies').DataTable({
        ajax: {
            url: "/empty_table",
            method: "POST",
            data: function() {
                    return JSON.stringify({
                        'dateSelector':$("[name='date']:checked").val(),
                        'startDate': $("#startDate").val(),
                        'endDate': $("#endDate").val(),
                        'device': devices_table.rows({ selected: true }).data()[0].name,
                        'modalities': $("[name='modality']:checked").map(function() {
                            return this.value
                        }).get(),
                        'searchField':$( "#search-field" ).val(),
                        'searchValue':$("#search-value").val()
                    })
                },
            contentType: 'application/json',
            dataType: "json"
          },              
        columns: [
            {
                className: 'dt-control',
                orderable: false,
                data: null,
                defaultContent: '',
            },
            { data: 'PatientName', title: 'Paciente' },
            { data: 'PatientID', title: 'ID' },
            { data: 'StudyDate', title: 'Fecha', type: 'date'},
            { data: 'StudyTime', title: 'Hora' },
            { data: 'ModalitiesInStudy', title: 'Modalidades' },
            { data: 'StudyDescription', title: 'Descripcion' },
            { data: 'ImgsStudy', title: 'Imgs' }
        ],
        order: [[3, 'asc'],[4, 'asc']],
        language: {
            search: 'Buscar',
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: " ",
            processing: " ",
        },
        processing: true,  
        paging: false,
        scrollY: '300px',
        filter: false,
        initComplete: function() {
            // Change ajax target
            table_studies.ajax.url('/search_studies')
            // Initialize table with data stored locally
            if (localStorage.getItem('studiesTable') !== null) {
                data = JSON.parse(localStorage.getItem('studiesTable'))
                table_studies.rows.add(data).draw()                
            }
        }
    });

    // Manage the study search (form submission)
    $("#search_studies").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();
        // Reload table
        table_studies.clear().draw()
        //Store the query data to be shown after refreshing the page
        sourceDevice = devices_table.rows({ selected: true })[0]
        dateSelector = $("[name='date']:checked").prop('id')
        startDate = $("#startDate").val()
        endDate = $("#endDate").val()
        modalities = $("[name='modality']:checked").map(function() {
            return this.value
        }).get(),
        
        table_studies.ajax.reload( function() {
            // Store the data locally to be shown after refreshing the page    
            localStorage.setItem("studiesTable",JSON.stringify(table_studies.rows().data().toArray()))
            localStorage.setItem("sourceDevice", sourceDevice)
            localStorage.setItem("dateSelector", dateSelector)
            localStorage.setItem("startDate", startDate)
            localStorage.setItem("endDate", endDate)
            localStorage.setItem("modalities", JSON.stringify(modalities))
        })
    });   
    
    // Add event listener for opening and closing details
    $('#studies tbody').on('click', 'td.dt-control', function () {
        var tr = $(this).closest('tr');
        var row = table_studies.row(tr);
 
        if (row.child.isShown()) {
            // This row is already open - close it
            row.child.hide();
            tr.removeClass('shown');
        } else {
            // Open this row
            showStudy(row)            
            tr.addClass('shown');
        }
    });  
    
    // Add row selection behaviour
    $('#studies tbody').on('click', 'tr', function (clickEvent) {  
              
        if (($(this).hasClass('odd') || $(this).hasClass('even')) && !clickEvent.target.classList.contains('dt-control')) {
            $(this).toggleClass('selected toSend');            
        }

    });

    // Add send button behaviour
    $("#sendForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();

        // Get destination device
        var ajax_data = {'destination': $("#destinations").val()}

        // Get selected rows
        var items = []
        var tr = $('.toSend')        
        for (var idx = 0; idx < tr.length; idx++){
            var element = tr[idx]
            items.push($(element.closest('table')).DataTable().row(element).data())                        
        }
        ajax_data.items = items
        console.log(ajax_data)
        $.ajax({
            url: "/move",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {
                
                // Show success message
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });

    });
}

function initDestinations() {
    var selectValues = $('#devices').DataTable().column(0).data()
    $.each(selectValues, function(key, value) {
        $('#destinations')
             .append($('<option>', { value : value })
             .text(value));
   });
}

// Show study details
function showStudy(row) {        
    
    row.child(`<table id="child_${row.data().StudyInstanceUID}" class="display compact" width="100%"> 
                
            </table>`).show();
    var childTable = $(jq("child_" + row.data().StudyInstanceUID)).DataTable({
        ajax: {
        url: "/get_study_data",
        method: "POST",
        data: function() { return JSON.stringify(row.data()) },
        contentType: 'application/json',
        dataType: "json"
      },
        columns: [
            
            { data: 'SeriesNumber', title: 'Numero' },
            { data: 'SeriesDate', title: 'Fecha' },
            { data: 'SeriesTime', title: 'Hora' },
            { data: 'SeriesDescription', title: 'Descripcion' },
            { data: 'Modality', title: 'Modalidad' },
            { data: 'ImgsSeries', title:'Imgs' },
            
        ],
        order: [[0, 'asc']],
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: "<br><br>",
            processing: " ",
            loadingRecords: "<br>",
        },
        processing: true,
        paging: false,
        filter: false,
        info: false,
});
}

// Escape special characters in html element id (to be usable by jQuery)
function jq( myid ) {  
    return "#" + myid.replace( /(:|\.|\[|\]|,|=|@)/g, "\\$1" ); 
}

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';